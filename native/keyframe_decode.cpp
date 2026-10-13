// Managed all-IDR worker. Python owns cache, cancellation and fallback.
extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavfilter/avfilter.h>
#include <libavfilter/buffersrc.h>
#include <libavfilter/buffersink.h>
#include <libavutil/opt.h>
#include <libavutil/pixdesc.h>
}
#include <cstdint>
#include <chrono>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

struct Unsupported : std::runtime_error { using std::runtime_error::runtime_error; };
struct Failure : std::runtime_error { using std::runtime_error::runtime_error; };
static void checked(int rc, const char* message) { if(rc<0) throw Failure(message); }
static void checked_input(int rc, const char* message) {
    if(rc==AVERROR_INVALIDDATA || rc==AVERROR(EINVAL)) throw Unsupported(message);
    checked(rc,message);
}
static void bytes(const void* data, size_t length) {
    if(fwrite(data,1,length,stdout)!=length) throw Failure("output write failed");
}
static void le(uint64_t value, unsigned size) {
    uint8_t data[8]; for(unsigned i=0;i<size;i++) data[i]=(value>>(8*i))&255;
    bytes(data,size);
}
static int number(const char* text) {
    char* end=nullptr; long value=strtol(text,&end,10);
    if(!text[0] || *end || value<0 || value>std::numeric_limits<int>::max())
        throw Failure("invalid argument");
    return static_cast<int>(value);
}
static int avcc_length(const AVCodecParameters* par) {
    if(par->codec_id!=AV_CODEC_ID_H264 || par->extradata_size<7 ||
       par->extradata[0]!=1) throw Unsupported("requires H.264 AVCC");
    const uint8_t* d=par->extradata; size_t size=par->extradata_size, pos=6;
    int length=(d[4]&3)+1;
    if(length==3) throw Unsupported("reserved AVCC NAL length");
    auto sets=[&](unsigned count, int type) {
        if(!count) throw Unsupported("missing parameter sets");
        while(count--) {
            if(pos+2>size) throw Unsupported("truncated AVCC");
            unsigned n=(d[pos]<<8)|d[pos+1];pos+=2;
            if(!n || n>size-pos) throw Unsupported("invalid AVCC parameter set");
            if((d[pos]&128) || (d[pos]&31)!=type) throw Unsupported("invalid AVCC parameter-set type");
            pos+=n;
        }
    };
    sets(d[5]&31,7);
    if(pos>=size) throw Unsupported("missing AVCC PPS");
    unsigned pps=d[pos++];sets(pps,8);
    return length;
}
static bool is_idr(const AVPacket* packet, int length, bool require_stable=false) {
    size_t pos=0,size=packet->size; bool found=false, other_vcl=false;
    while(pos<size) {
        if(size-pos<static_cast<size_t>(length)) throw Unsupported("truncated NAL length");
        uint32_t n=0;for(int i=0;i<length;i++) n=(n<<8)|packet->data[pos++];
        if(!n || n>size-pos) throw Unsupported("invalid NAL length");
        uint8_t head=packet->data[pos];int type=head&31;
        if(head&128) throw Unsupported("invalid NAL header");
        if(require_stable && (type==6 || type==7 || type==8))
            throw Unsupported("half selection requires stable configuration without later SEI");
        found|=type==5;other_vcl|=type>=1 && type<=4;
        pos+=n;
    }
    if(other_vcl) return false;
    return found;
}
struct Worker {
    AVFormatContext* fmt=nullptr; AVCodecContext* codec=nullptr;
    AVPacket* packet=av_packet_alloc(); AVFrame* frame=av_frame_alloc();
    AVFrame* output=av_frame_alloc(); AVFilterGraph* graph=nullptr;
    AVFilterContext* input=nullptr; AVFilterContext* sink=nullptr;
    ~Worker() {
        avfilter_graph_free(&graph);av_frame_free(&output);av_frame_free(&frame);
        av_packet_free(&packet);avcodec_free_context(&codec);avformat_close_input(&fmt);
    }
    void init_filter(AVRational tb, const char* filter) {
        graph=avfilter_graph_alloc();if(!graph) throw Failure("graph allocation");
        // Match FFmpeg's automatic filter threading for the same canonical graph.
        char args[256];
        AVRational sar=frame->sample_aspect_ratio;
        if(sar.num<=0 || sar.den<=0) sar={1,1};
        snprintf(args,sizeof(args),"video_size=%dx%d:pix_fmt=%d:time_base=%d/%d:pixel_aspect=%d/%d",
            frame->width,frame->height,frame->format,tb.num,tb.den,sar.num,sar.den);
        checked(avfilter_graph_create_filter(&input,avfilter_get_by_name("buffer"),"in",args,nullptr,graph),"buffer");
        checked(avfilter_graph_create_filter(&sink,avfilter_get_by_name("buffersink"),"out",nullptr,nullptr,graph),"sink");
        AVFilterInOut* outputs=avfilter_inout_alloc();AVFilterInOut* inputs=avfilter_inout_alloc();
        if(!outputs || !inputs) {avfilter_inout_free(&outputs);avfilter_inout_free(&inputs);throw Failure("filter endpoint allocation");}
        outputs->name=av_strdup("in");outputs->filter_ctx=input;outputs->pad_idx=0;
        inputs->name=av_strdup("out");inputs->filter_ctx=sink;inputs->pad_idx=0;
        int rc=avfilter_graph_parse_ptr(graph,filter,&inputs,&outputs,nullptr);
        avfilter_inout_free(&inputs);avfilter_inout_free(&outputs);
        checked(rc,"filter parse");checked(avfilter_graph_config(graph,nullptr),"filter configure");
    }
};
int main(int argc,char**argv) {
    if(argc==2 && !strcmp(argv[1],"-version")) {
        printf("slide-keyframe-decode FFmpeg %s\nconfiguration: %s\nlicense: %s\n",
               av_version_info(),avcodec_configuration(),avcodec_license());
        return 0;
    }
    av_log_set_level(AV_LOG_ERROR);
#ifdef _WIN32
    _setmode(_fileno(stdout),_O_BINARY);
#endif
    try {
        if(argc!=6 && argc!=7) throw Failure("usage: helper source stream filter width height");
        int stream=number(argv[2]), width=number(argv[4]),height=number(argv[5]);
        if(width<1 || width>640 || height<1 || height>16384) throw Failure("output dimensions");
        int stride=argc==7 ? number(argv[6]) : 1;
        if(stride!=1 && stride!=2) throw Failure("unsupported selection stride");
        Worker w;
        if(!w.packet || !w.frame || !w.output) throw Failure("allocation");
        checked(avformat_open_input(&w.fmt,argv[1],nullptr,nullptr),"open source");
        checked(avformat_find_stream_info(w.fmt,nullptr),"stream info");
        if(stream>=static_cast<int>(w.fmt->nb_streams)) throw Unsupported("stream unavailable");
        AVStream* st=w.fmt->streams[stream];const AVCodecParameters* par=st->codecpar;
        int length=avcc_length(par);
        const AVCodec* decoder=avcodec_find_decoder(par->codec_id);
        if(!decoder) throw Unsupported("decoder unavailable");
        w.codec=avcodec_alloc_context3(decoder);if(!w.codec) throw Failure("decoder allocation");
        checked(avcodec_parameters_to_context(w.codec,par),"codec parameters");
        w.codec->thread_count=1;w.codec->pkt_timebase=st->time_base;
        checked_input(avcodec_open2(w.codec,decoder,nullptr),"decoder open");
        AVRational tb=st->time_base;
        if(tb.num<=0 || tb.den<=0) throw Failure("invalid time base");
        bytes("SEKF0001",8);uint64_t count=0, packets=0, keyframes=0;
        int64_t previous=AV_NOPTS_VALUE;int format=-1;
        int matrix=-1,range=-1,transfer=-1,primaries=-1;
        AVRational observed_sar={0,1};
        auto last_report=std::chrono::steady_clock::now();
        int rc;
        while((rc=av_read_frame(w.fmt,w.packet))>=0) {
            ++packets;
            auto now=std::chrono::steady_clock::now();
            if(packets%100==0 || now-last_report>=std::chrono::seconds(1)) {
                le(3,1);le(packets,8);fflush(stdout);last_report=now;
            }
            if(w.packet->stream_index==stream) {
                if(w.packet->flags&AV_PKT_FLAG_CORRUPT) throw Unsupported("corrupt packet");
                size_t extra_size=0;
                if(av_packet_get_side_data(w.packet,AV_PKT_DATA_NEW_EXTRADATA,&extra_size))
                    throw Unsupported("dynamic codec configuration");
                if(stride==2 && keyframes>0)
                    is_idr(w.packet,length,true);
                if(w.packet->flags&AV_PKT_FLAG_KEY) {
                    if(!is_idr(w.packet,length)) throw Unsupported("non-IDR key packet");
                    uint64_t source_ordinal=keyframes++;
                    // Validate every key packet, including those not decoded.
                    if(source_ordinal%stride) {av_packet_unref(w.packet);continue;}
                    avcodec_flush_buffers(w.codec);
                    checked_input(avcodec_send_packet(w.codec,w.packet),"send IDR");
                    checked_input(avcodec_send_packet(w.codec,nullptr),"drain decoder");
                    unsigned decoded=0;
                    while((rc=avcodec_receive_frame(w.codec,w.frame))>=0) {
                        ++decoded;
                        if(decoded!=1 || !(w.frame->flags&AV_FRAME_FLAG_KEY)) throw Unsupported("unexpected IDR output");
                        if(w.frame->width!=par->width || w.frame->height!=par->height ||
                           (w.frame->flags&AV_FRAME_FLAG_INTERLACED)) throw Unsupported("dynamic/interlaced frame");
                        if(format!=-1 && format!=w.frame->format) throw Unsupported("dynamic pixel format");
                        format=w.frame->format;
                        AVRational sar=w.frame->sample_aspect_ratio;
                        if(sar.num<=0 || sar.den<=0) sar={1,1};
                        if(observed_sar.num && av_cmp_q(sar,observed_sar))
                            throw Unsupported("dynamic sample aspect ratio");
                        observed_sar=sar;
                        if(w.frame->color_trc==AVCOL_TRC_SMPTE2084 || w.frame->color_trc==AVCOL_TRC_ARIB_STD_B67 ||
                           w.frame->colorspace==AVCOL_SPC_BT2020_NCL || w.frame->colorspace==AVCOL_SPC_BT2020_CL)
                            throw Unsupported("HDR frame metadata");
                        auto stable=[](int& previous,int value,int unspecified) {
                            if(value==unspecified) return;
                            if(previous!=-1 && previous!=value) throw Unsupported("dynamic color metadata");
                            previous=value;
                        };
                        stable(matrix,w.frame->colorspace,AVCOL_SPC_UNSPECIFIED);
                        stable(range,w.frame->color_range,AVCOL_RANGE_UNSPECIFIED);
                        stable(transfer,w.frame->color_trc,AVCOL_TRC_UNSPECIFIED);
                        stable(primaries,w.frame->color_primaries,AVCOL_PRI_UNSPECIFIED);
                        int64_t pts=w.frame->pts;
                        if(pts==AV_NOPTS_VALUE || (previous!=AV_NOPTS_VALUE && pts<=previous))
                            throw Failure("invalid decoded PTS");
                        previous=pts;
                        if(!w.graph) w.init_filter(tb,argv[3]);
                        checked(av_buffersrc_add_frame_flags(w.input,w.frame,AV_BUFFERSRC_FLAG_KEEP_REF),"filter input");
                        checked(av_buffersink_get_frame(w.sink,w.output),"filter output");
                        if(w.output->width!=width || w.output->height!=height || w.output->format!=AV_PIX_FMT_RGB24 ||
                           w.output->pts!=pts || av_cmp_q(av_buffersink_get_time_base(w.sink),tb))
                            throw Failure("transformed geometry/PTS mismatch");
                        le(1,1);le(static_cast<uint64_t>(pts),8);le(source_ordinal,8);
                        le(tb.num,4);le(tb.den,4);le(width,4);le(height,4);le(uint64_t(width)*height*3,4);
                        for(int y=0;y<height;y++) bytes(w.output->data[0]+y*w.output->linesize[0],width*3);
                        fflush(stdout);
                        ++count;av_frame_unref(w.output);av_frame_unref(w.frame);
                    }
                    if(rc!=AVERROR_EOF || decoded!=1) throw Unsupported("IDR did not decode independently");
                }
            }
            av_packet_unref(w.packet);
        }
        if(rc!=AVERROR_EOF || !count) throw Failure("demux failure or empty IDR stream");
        le(2,1);le(count,8);if(fflush(stdout)) throw Failure("flush failed");
        return 0;
    } catch(const Unsupported& e) {fprintf(stderr,"unsupported: %s\n",e.what());return 20;}
      catch(const std::exception& e) {fprintf(stderr,"failed: %s\n",e.what());return 21;}
}

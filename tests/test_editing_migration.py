"""Editing contracts migrated from the retired timestamp engine."""
from tests.test_gui_sync import create
from slide_core.editing import add_page,replace_page,delete_page,nearest_sample

def test_insert_keeps_time_order_and_no_duplicates(tmp_path):
    p=create(tmp_path);add_page(p,1.1);assert [p.sample_time(x.representative_sample_id) for x in p.pages]==[0,1,2]
    assert add_page(p,1.1).status=='no_op' and len(p.pages)==3

def test_replace_resorts_and_removal(tmp_path):
    p=create(tmp_path);first=p.pages[0].page_id;replace_page(p,first,3)
    assert [p.sample_time(x.representative_sample_id) for x in p.pages]==[2,3]
    delete_page(p,first);assert [p.sample_time(x.representative_sample_id) for x in p.pages]==[2]

def test_nearest_sample(tmp_path):
    p=create(tmp_path);assert nearest_sample(p,2.8).actual_time==3

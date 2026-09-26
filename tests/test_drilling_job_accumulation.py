"""Real multi-tool job assembly must not append a previous job's output."""
from contextlib import nullcontext
import logging
from types import SimpleNamespace

import pytest
from shapely.geometry import Point


def make_job():
    # A deterministic CAM boundary isolates the application's assembly of two tool outputs.
    job = SimpleNamespace(kind='cncjob', geo_steps_per_circle=8, obj_options={}, postdata={},
                           xy_end=[0, 0], measured_distance=0, measured_down_distance=0,
                           measured_up_to_zero_distance=0, measured_lift_distance=0,
                           z_feedrate=60, feedrate_rapid=300, create_geometry=lambda: None)
    def generate(tool, points, tools, **kwargs):
        return f'T{tool}\nG1 X{points[0].x} Y{points[0].y}\n', (points[-1].x, points[-1].y), ''
    job.excellon_tool_gcode_gen = generate
    job.excellon_tool_gcode_parse = lambda diameter, gcode, **kwargs: [dict(diameter=diameter, gcode=gcode)]
    return job


@pytest.mark.parametrize('queue_both', [False, True], ids=['sequential', 'already-queued'])
def test_repeated_multitool_generation_has_independent_output(queue_both):
    from appPlugins.ToolDrilling import ToolDrilling
    jobs, pending = [], []
    source = SimpleNamespace(obj_options=dict(name='board', xmin=0, ymin=0, xmax=3, ymax=4))
    app = SimpleNamespace(log=logging.getLogger('drill-assembly'), options={'excellon_optimization_type': 'N'},
        inform=SimpleNamespace(emit=lambda *args: None), preprocessors={'default': object()},
        collection=SimpleNamespace(get_by_name=lambda name: source, promise=lambda name: None),
        exc_areas=SimpleNamespace(exclusion_areas_storage=[]),
        worker_task=SimpleNamespace(emit=pending.append),
        proc_container=SimpleNamespace(new=lambda text: nullcontext()),
        ui=SimpleNamespace(notebook=SimpleNamespace(setCurrentWidget=lambda widget: None), properties_tab=None))
    def new_object(kind, name, initialize):
        job = make_job()
        initialize(job, app)
        jobs.append(job)
    app.app_obj = SimpleNamespace(new_object=new_object)
    tools = {identifier: dict(tooldia=diameter, drills=[Point(identifier, identifier + 1)], slots=[],
              data=dict(tools_drill_toolchange=True, tools_drill_drill_slots=False, tools_drill_toolchangexy='0,0'))
             for identifier, diameter in [(1, .8), (2, 1.0)]}
    tool = SimpleNamespace(app=app, excellon_tools=tools, total_gcode='', total_gcode_parsed=[],
        ui=SimpleNamespace(object_combo=SimpleNamespace(currentText=lambda: 'board'),
                            pp_excellon_name_cb=SimpleNamespace(get_value=lambda: 'default'),
                            order_combo=SimpleNamespace(get_value=lambda: 0),
                            last_drill_cb=SimpleNamespace(get_value=lambda: False)),
        is_valid_excellon=lambda: True, get_selected_tools_uid=lambda: [1, 2])
    tool.create_drill_points = lambda **kwargs: ToolDrilling.create_drill_points(tool, **kwargs)
    for _ in range(2):
        ToolDrilling.on_generate_cnc_job(tool)
        if queue_both:
            continue
        request = pending.pop(0)
        request['fcn'](*request['params'])
    for request in pending:
        request['fcn'](*request['params'])
    assert len(jobs) == 2 and jobs[0].gcode
    assert jobs[1].gcode == jobs[0].gcode
    assert jobs[1].source_file == jobs[0].source_file
    assert jobs[1].gcode_parsed == jobs[0].gcode_parsed
    assert jobs[0].gcode_parsed is not jobs[1].gcode_parsed
    assert len(jobs[0].gcode_parsed) == len(jobs[1].gcode_parsed) == 2

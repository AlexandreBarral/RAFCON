import sys
import logging
import gtk
import threading
from os.path import join

# gui elements
import rafcon.gui.config as gui_config
import rafcon.gui.singleton
from rafcon.gui.controllers.main_window import MainWindowController
from rafcon.gui.views.main_window import MainWindowView
from rafcon.gui.views.graphical_editor import GraphicalEditor as OpenGLEditor
from rafcon.gui.mygaphas.view import ExtendedGtkView as GaphasEditor
import rafcon.gui.state_machine_helper as state_machine_helper

# core elements
import rafcon.core.config
from rafcon.core.states.hierarchy_state import HierarchyState
from rafcon.core.states.execution_state import ExecutionState
from rafcon.core.states.library_state import LibraryState
from rafcon.core.state_machine import StateMachine
import rafcon.core.singleton

# general tool elements
from rafcon.utils import log

# test environment elements
import testing_utils
from testing_utils import call_gui_callback

import pytest

logger = log.get_logger(__name__)


def create_models(*args, **kargs):

    state1 = ExecutionState('State1')
    state2 = ExecutionState('State2')
    state4 = ExecutionState('Nested')
    output_state4 = state4.add_output_data_port("out", "int")
    state5 = ExecutionState('Nested2')
    input_state5 = state5.add_input_data_port("in", "int", 0)
    state3 = HierarchyState(name='State3')
    state3.add_state(state4)
    state3.add_state(state5)
    state3.set_start_state(state4)
    state3.add_scoped_variable("share", "int", 3)
    state3.add_transition(state4.state_id, 0, state5.state_id, None)
    state3.add_transition(state5.state_id, 0, state3.state_id, 0)
    state3.add_data_flow(state4.state_id, output_state4, state5.state_id, input_state5)

    ctr_state = HierarchyState(name="Container")
    ctr_state.add_state(state1)
    ctr_state.add_state(state2)
    ctr_state.add_state(state3)
    ctr_state.set_start_state(state1)
    ctr_state.add_transition(state1.state_id, 0, state2.state_id, None)
    ctr_state.add_transition(state2.state_id, 0, state3.state_id, None)
    ctr_state.add_transition(state3.state_id, 0, ctr_state.state_id, 0)
    ctr_state.name = "Container"

    return ctr_state


def focus_graphical_editor_in_page(page):
    graphical_controller = page.children()[0]
    if not isinstance(graphical_controller, (OpenGLEditor, GaphasEditor)):
        graphical_controller = graphical_controller.children()[0]
    graphical_controller.grab_focus()


def select_and_paste_state(state_machine_model, source_state_model, target_state_model, menu_bar_ctrl, operation,
                           main_window_controller, page):
    """Select a particular state and perform an operation on it (Copy or Cut) and paste it somewhere else. At the end,
    verify that the operation was completed successfully.

    :param state_machine_model: The state machine model where the operation will be conducted
    :param source_state_model: The state model, on which the operation will be performed
    :param target_state_model: The state model, where the source state will be pasted
    :param menu_bar_ctrl: The menu_bar controller, through which copy, cut & paste actions are triggered
    :param operation: String indicating the operation to be performed (Copy or Cut)
    :param main_window_controller: The MainWindow Controller
    :param page: The notebook page of the corresponding state machine in the state machines editor
    :return: The target state model, and the child state count before pasting
    """
    print "\n\n %s \n\n" % source_state_model.state.name
    call_gui_callback(state_machine_model.selection.set, [source_state_model])
    call_gui_callback(getattr(menu_bar_ctrl, 'on_{}_selection_activate'.format(operation)), None, None)
    print "\n\n %s \n\n" % target_state_model.state.name
    call_gui_callback(state_machine_model.selection.set, [target_state_model])
    old_child_state_count = len(target_state_model.state.states)
    main_window_controller.view['main_window'].grab_focus()
    focus_graphical_editor_in_page(page)
    call_gui_callback(menu_bar_ctrl.on_paste_clipboard_activate, None, None)
    testing_utils.wait_for_gui()
    print target_state_model.state.states.keys()
    assert len(target_state_model.state.states) == old_child_state_count + 1
    return target_state_model, old_child_state_count


def copy_and_paste_state_into_itself(sm_m, state_m_to_copy, page, menu_bar_ctrl):
    call_gui_callback(sm_m.selection.set, [state_m_to_copy])
    focus_graphical_editor_in_page(page)
    call_gui_callback(menu_bar_ctrl.on_copy_selection_activate, None, None)
    old_child_state_count = len(state_m_to_copy.state.states)
    call_gui_callback(sm_m.selection.set, [state_m_to_copy])
    focus_graphical_editor_in_page(page)
    call_gui_callback(menu_bar_ctrl.on_paste_clipboard_activate, None, None)
    assert len(state_m_to_copy.state.states) == old_child_state_count + 1


@log.log_exceptions(None, gtk_quit=True)
def trigger_gui_signals(*args):
    """The function triggers and test basic functions of the menu bar.

    At the moment those functions are tested:
    - New State Machine
    - Open State Machine
    - Copy State/HierarchyState -> via GraphicalEditor
    - Cut State/HierarchyState -> via GraphicalEditor
    - Paste State/HierarchyState -> via GraphicalEditor
    - Refresh Libraries
    - Refresh All
    - Save as
    - Stop State Machine
    - Quit GUI
    """

    sm_manager_model = args[0]
    main_window_controller = args[1]
    menubar_ctrl = main_window_controller.get_controller('menu_bar_controller')

    current_sm_length = len(sm_manager_model.state_machines)
    first_sm_id = sm_manager_model.state_machines.keys()[0]
    call_gui_callback(menubar_ctrl.on_new_activate, None)

    assert len(sm_manager_model.state_machines) == current_sm_length + 1
    call_gui_callback(menubar_ctrl.on_open_activate, None, None, join(rafcon.__path__[0],
                                                                      "../test_scripts/tutorials/basic_turtle_demo_sm"))
    assert len(sm_manager_model.state_machines) == current_sm_length + 2

    sm_m = sm_manager_model.state_machines[first_sm_id + 2]
    testing_utils.wait_for_gui()
    # MAIN_WINDOW NEEDS TO BE FOCUSED (for global input focus) TO OPERATE PASTE IN GRAPHICAL VIEWER
    main_window_controller.view['main_window'].grab_focus()
    sm_manager_model.selected_state_machine_id = first_sm_id + 2
    state_machines_ctrl = main_window_controller.get_controller('state_machines_editor_ctrl')
    page_id = state_machines_ctrl.get_page_id(first_sm_id + 2)
    page = state_machines_ctrl.view.notebook.get_nth_page(page_id)
    focus_graphical_editor_in_page(page)
    testing_utils.wait_for_gui()

    #########################################################
    print "select & copy an execution state -> and paste it somewhere"
    select_and_paste_state(sm_m, sm_m.get_state_model_by_path('CDMJPK/RMKGEW/KYENSZ'), sm_m.get_state_model_by_path(
        'CDMJPK/RMKGEW'), menubar_ctrl, 'copy', main_window_controller, page)

    ###########################################################
    print "select & copy a hierarchy state -> and paste it some where"
    select_and_paste_state(sm_m, sm_m.get_state_model_by_path('CDMJPK/RMKGEW/KYENSZ/VCWTIY'),
                           sm_m.get_state_model_by_path('CDMJPK'), menubar_ctrl, 'copy', main_window_controller, page)

    ##########################################################
    print "select a library state -> and paste it some where WITH CUT !!!"
    state_m, old_child_state_count = select_and_paste_state(sm_m,
                                                            sm_m.get_state_model_by_path('CDMJPK/RMKGEW/KYENSZ/VCWTIY'),
                                                            sm_m.get_state_model_by_path('CDMJPK'), menubar_ctrl, 'cut',
                                                            main_window_controller, page)

    ##########################################################
    # create complex state with all elements
    lib_state = LibraryState("generic/dialog", "Dialog [3 options]", "0.1", "Dialog [3 options]")
    call_gui_callback(state_machine_helper.insert_state, lib_state, True)
    assert len(state_m.state.states) == old_child_state_count + 2

    for state in state_m.state.states.values():
        if state.name == "Dialog [3 options]":
            break
    new_template_state = state
    call_gui_callback(new_template_state.add_scoped_variable, 'scoopy', float, 0.3)
    state_m_to_copy = sm_m.get_state_model_by_path('CDMJPK/' + new_template_state.state_id)

    ##########################################################
    print "copy & paste complex state into itself"

    copy_and_paste_state_into_itself(sm_m, state_m_to_copy, page, menubar_ctrl)
    print "increase complexity by doing it twice -> increase the hierarchy-level"
    copy_and_paste_state_into_itself(sm_m, state_m_to_copy, page, menubar_ctrl)

    ##########################################################
    # group states
    # TODO improve test to related data flows
    state_m_parent = sm_m.get_state_model_by_path('CDMJPK/RMKGEW/KYENSZ')
    state_ids_old = [state_id for state_id in state_m_parent.state.states]
    call_gui_callback(state_m_parent.state.group_states, ['PAYECU', 'UEPNNW', 'KQDJYS'])

    ##########################################################
    # ungroup new state
    state_new = None
    for state_id in state_m_parent.state.states:
        if state_id not in state_ids_old:
            state_new = state_m_parent.state.states[state_id]
    call_gui_callback(state_m_parent.state.ungroup_state, state_new.state_id)

    ##########################################################
    # substitute state with template
    lib_state = rafcon.gui.singleton.library_manager.get_library_instance('generic', 'wait')
    old_keys = state_m_parent.state.states.keys()
    transitions_before, data_flows_before = state_m_parent.state.related_linkage_state('RQXPAI')
    call_gui_callback(state_m_parent.state.substitute_state, 'RQXPAI', lib_state.state_copy)
    new_state_id = None
    for state_id in state_m_parent.state.states.keys():
        if state_id not in old_keys:
            new_state_id = state_id
    transitions_after, data_flows_after = state_m_parent.state.related_linkage_state(new_state_id)
    # transition is not preserved because of unequal outcome naming
    assert len(transitions_before['external']['ingoing']) == 1
    assert len(transitions_after['external']['ingoing']) == 1
    assert len(transitions_before['external']['outgoing']) == 1
    assert len(transitions_after['external']['outgoing']) == 0
    call_gui_callback(state_m_parent.state.add_transition, new_state_id, 0, 'MCOLIQ', None)

    # modify the template with other data type and respective data flows to parent
    state_m_parent.states[new_state_id].state.input_data_ports.items()[0][1].data_type = "int"
    call_gui_callback(state_m_parent.state.add_input_data_port, 'in_time', "int")
    call_gui_callback(state_m_parent.state.add_data_flow,
                      state_m_parent.state.state_id,
                      state_m_parent.state.input_data_ports.items()[0][1].data_port_id,
                      new_state_id,
                      state_m_parent.states[new_state_id].state.input_data_ports.items()[0][1].data_port_id)

    old_keys = state_m_parent.state.states.keys()
    transitions_before, data_flows_before = state_m_parent.state.related_linkage_state(new_state_id)
    lib_state = rafcon.gui.singleton.library_manager.get_library_instance('generic', 'wait')
    call_gui_callback(state_m_parent.state.substitute_state, new_state_id, lib_state)
    new_state_id = None
    for state_id in state_m_parent.state.states.keys():
        if state_id not in old_keys:
            new_state_id = state_id
    transitions_after, data_flows_after = state_m_parent.state.related_linkage_state(new_state_id)
    # test if data flow is ignored
    assert len(transitions_before['external']['ingoing']) == 1
    assert len(transitions_after['external']['ingoing']) == 1
    assert len(transitions_before['external']['outgoing']) == 1
    assert len(transitions_after['external']['outgoing']) == 1
    assert len(data_flows_before['external']['ingoing']) == 1
    assert len(data_flows_after['external']['ingoing']) == 0

    # data flow is preserved if right data type and name is used
    state_m_parent.state.input_data_ports.items()[0][1].data_type = "float"
    if isinstance(state_m_parent.state.states[new_state_id], LibraryState):
        data_port_id = state_m_parent.state.states[new_state_id].input_data_ports.items()[0][0]
        state_m_parent.state.states[new_state_id].use_runtime_value_input_data_ports[data_port_id] = True
        state_m_parent.state.states[new_state_id].input_data_port_runtime_values[data_port_id] = 2.0
        print
    else:
        raise
        # state_m_parent.state.states[new_state_id].input_data_ports.items()[0][1].default_value = 2.0
    call_gui_callback(state_m_parent.state.add_data_flow,
                      state_m_parent.state.state_id,
                      state_m_parent.state.input_data_ports.items()[0][1].data_port_id,
                      new_state_id,
                      state_m_parent.states[new_state_id].state.input_data_ports.items()[0][1].data_port_id)

    old_keys = state_m_parent.state.states.keys()
    transitions_before, data_flows_before = state_m_parent.state.related_linkage_state(new_state_id)
    lib_state = rafcon.gui.singleton.library_manager.get_library_instance('generic', 'wait')
    call_gui_callback(state_m_parent.state.substitute_state, new_state_id, lib_state.state_copy)
    new_state_id = None
    for state_id in state_m_parent.state.states.keys():
        if state_id not in old_keys:
            new_state_id = state_id
    transitions_after, data_flows_after = state_m_parent.state.related_linkage_state(new_state_id)
    # test if data flow is ignored
    assert len(transitions_before['external']['ingoing']) == 1
    assert len(transitions_after['external']['ingoing']) == 1
    assert len(transitions_before['external']['outgoing']) == 1
    assert len(transitions_after['external']['outgoing']) == 1
    assert len(data_flows_before['external']['ingoing']) == 1
    assert len(data_flows_after['external']['ingoing']) == 1
    assert state_m_parent.state.states[new_state_id].input_data_ports.items()[0][1].default_value == 2.0

    call_gui_callback(menubar_ctrl.on_refresh_libraries_activate, None)
    call_gui_callback(menubar_ctrl.on_refresh_all_activate, None, None, True)
    assert len(sm_manager_model.state_machines) == 1

    call_gui_callback(menubar_ctrl.on_save_as_activate, None, None, testing_utils.get_unique_temp_path())
    call_gui_callback(menubar_ctrl.on_stop_activate, None)
    call_gui_callback(menubar_ctrl.on_quit_activate, None)


def test_gui(caplog):
    testing_utils.start_rafcon()
    testing_utils.remove_all_libraries()
    library_paths = rafcon.core.config.global_config.get_config_value("LIBRARY_PATHS")
    gui_config.global_gui_config.set_config_value('HISTORY_ENABLED', False)
    gui_config.global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    library_paths["ros"] = join(rafcon.__path__[0], "../test_scripts/ros_libraries")
    library_paths["turtle_libraries"] = join(rafcon.__path__[0], "../test_scripts/turtle_libraries")
    library_paths["generic"] = join(rafcon.__path__[0], "../libraries/generic")
    rafcon.core.singleton.library_manager.refresh_libraries()

    ctr_state = create_models()
    state_machine = StateMachine(ctr_state)
    rafcon.core.singleton.state_machine_manager.add_state_machine(state_machine)

    testing_utils.sm_manager_model = rafcon.gui.singleton.state_machine_manager_model
    main_window_view = MainWindowView()
    main_window_controller = MainWindowController(testing_utils.sm_manager_model, main_window_view)

    # Wait for GUI to initialize
    testing_utils.wait_for_gui()

    thread = threading.Thread(target=trigger_gui_signals, args=[testing_utils.sm_manager_model, main_window_controller])
    thread.start()
    gtk.main()
    logger.debug("after gtk main")
    thread.join()
    testing_utils.test_multithreading_lock.release()
    testing_utils.assert_logger_warnings_and_errors(caplog)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
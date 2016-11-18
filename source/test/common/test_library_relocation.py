#!/usr/bin/env python

import pytest
from pytest import raises
import testing_utils
import signal

import rafcon
from rafcon.statemachine import interface, start
from rafcon.statemachine.custom_exceptions import LibraryNotFoundException
from rafcon.statemachine.states.library_state import LibraryState
from rafcon.statemachine.storage import storage
import rafcon.statemachine.singleton as sm_singletons
# needed for yaml parsing
from rafcon.statemachine.states.hierarchy_state import HierarchyState
from rafcon.statemachine.states.execution_state import ExecutionState
from rafcon.statemachine.states.preemptive_concurrency_state import PreemptiveConcurrencyState
from rafcon.statemachine.states.barrier_concurrency_state import BarrierConcurrencyState
from rafcon.statemachine.execution.state_machine_execution_engine import StateMachineExecutionEngine
from rafcon.statemachine.enums import StateExecutionState

from rafcon.utils import log
logger = log.get_logger("start-no-gui")
logger.info("initialize RAFCON ... ")


def show_notice(query):
    return ""  # just take note of the missing library


def open_folder(query):
    if "library2_for_relocation_test" in query:
        return None  # the first relocation has to be aborted
    else:
        return testing_utils.get_test_sm_path("unit_test_state_machines/library_relocation_test_source/library1_for_relocation_test_relocated")


def test_library_relocation(caplog):

    signal.signal(signal.SIGINT, start.signal_handler)
    testing_utils.test_multithreading_lock.acquire()

    testing_utils.remove_all_libraries()

    library_paths = rafcon.statemachine.config.global_config.get_config_value("LIBRARY_PATHS")
    library_paths["test_scripts"] = testing_utils.TEST_SM_PATH

    # logger.debug(library_paths["test_scripts"])
    # exit()

    interface.open_folder_func = open_folder

    interface.show_notice_func = show_notice

    rafcon.statemachine.singleton.state_machine_manager.delete_all_state_machines()

    # Initialize libraries
    sm_singletons.library_manager.initialize()

    state_machine = storage.load_state_machine_from_path(testing_utils.get_test_sm_path(
        "unit_test_state_machines/library_relocation_test"))

    rafcon.statemachine.singleton.state_machine_manager.add_state_machine(state_machine)

    rafcon.statemachine.singleton.state_machine_execution_engine.start()
    rafcon.statemachine.singleton.state_machine_execution_engine.join()
    rafcon.statemachine.singleton.state_machine_execution_engine.stop()

    assert state_machine.root_state.output_data["output_0"] == 27

    testing_utils.assert_logger_warnings_and_errors(caplog, 0, 1)
    testing_utils.reload_config(config=True, gui_config=False)
    testing_utils.test_multithreading_lock.release()

    logger.info("State machine execution finished!")


def test_library_relocation_exception():
    logger.info("Load not existing library, expect exception to be raised...")
    with raises(LibraryNotFoundException):
        print LibraryState('aasdasd', 'basdasd', allow_user_interaction=False)


if __name__ == '__main__':
    pytest.main([__file__, '-s'])
from cascade.diagnostics.time.TimeMeasuring import TimeMeasuring
from cascade.diagnostics.logging.Logging import Logging
import time

class PhaseTimeMeasuring(TimeMeasuring):
    """
    Idea is that the following time-log tree:
        Analysis: 3min
            Phase 1 - 1min
                LLMcall -20sec
            Phase 2 - 2min

    can be achieved with the calls

    start - analysis
    start_phase - Phase 1
    start - LLMcall
    stop  - LLMcall
    start_phase - Phase 2
    stop  - analysis
    
    """
    def __init__(self, log:Logging, print_time_summary:bool=False):
        self.log=log.set_key("PhaseTime")
        self.stack=[]
        self.print_time_summary=print_time_summary

    def deepest_active_element(self) -> dict | None:
        if len(self.stack)<=0:
            return None
        
        element=self.stack[-1]

        if element["finish_time"]!=None:
            return None

        # Go down the tree recursively, stop at end or if child elements have stopped
        while len(element["parts"])>0 and element["parts"][-1]["finish_time"]==None:
            element=element["parts"][-1]

        return element

    def start(self, phase=""):
        start_time = time.perf_counter_ns()
        
        current_active=self.deepest_active_element()
        entry = {"phase":phase,"start_time":start_time,"finish_time":None,"parts":[]}
        if not current_active:
            self.stack.append(entry)
        else:
            current_active["parts"].append(entry)
        self.log.log_info(f"Starting Phase '{phase}'")
        return entry

    def stop(self, phase=""):
        if len(self.stack)<=0:
            self.log.log_error(f"There is no phase to stop.")
            return
        
        element=self.stack[-1]

        if element["finish_time"]!=None:
            return None

        # Go down the tree recursively, stop at end or if child elements have stopped
        while element["phase"]!=phase and len(element["parts"])>0 and element["parts"][-1]["finish_time"]==None:
            element=element["parts"][-1]

        #element is now the shallowest active phase with correct name or deepest active phase without correct name
        if not element or element["phase"]!=phase:
            self.log.log_error(f"Cannot find phase to stop '{phase}'")
            return
        
        to_stop = [element]

        while len(element["parts"])>0 and element["parts"][-1]["finish_time"]==None:
            element=element["parts"][-1]
            to_stop.append(element)
        
        finish_time=time.perf_counter_ns()
        for i in to_stop:
            i["finish_time"]=finish_time
        self.log.log_info(f"Finished Phase '{phase}' after {self.element_time_str(to_stop[0])}")

    
    # If the current phase was also started by this, stop it automatically
    def start_phase(self,phase=""):
        active = self.deepest_active_element()
        if active and "sub_phase" in active and active["sub_phase"]==True:
            self.stop(active["phase"])
        
        new_phase = self.start(phase)
        new_phase["sub_phase"]=True

        self.log.log_info(f"Started Phase {phase}")
        return new_phase

    def element_time_str(self, element:dict) -> str:
        if not element["finish_time"]:
            return "running"
        diff=element["finish_time"]-element["start_time"]
        if diff>10e3:
            return f"{diff/1e9}s"
        else:
            return f"{diff}ns"

    def time_summary_print(self,*args,**kwargs):
        if self.print_time_summary:
            self.log.log_info(*args,**kwargs)
        else:
            self.log.log_debug(*args,**kwargs)

    def log_element_tree(self,element:dict,indent=2):
        sub_phase_counter=1
        for i in element["parts"]:
            if "sub_phase" in i and i["sub_phase"]:
                self.time_summary_print((" "*indent)+f"{sub_phase_counter}. {i["phase"]}: {self.element_time_str(i)}")
                sub_phase_counter+=1
            else:
                self.time_summary_print((" "*indent)+f"- {i["phase"]}: {self.element_time_str(i)}")
            self.log_element_tree(i,indent+2)

    def log_summary(self):
        self.time_summary_print("Time usage Summary:")
        if len(self.stack)==0:
            self.time_summary_print("No phases were run")
        for i in self.stack:
            self.time_summary_print(f"- {i["phase"]}: {self.element_time_str(i)}")
            self.log_element_tree(i)

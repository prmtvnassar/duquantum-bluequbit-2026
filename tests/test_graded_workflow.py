from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from otoc.graded import candidates_for, select_record, plan_next
from otoc.bluequbit_adapter import BlueQubitAdapter
from otoc.experiment_store import digest


def settings():
    s=json.loads(Path("configs/workflow_v0.json").read_text())
    s.update(deadline_utc="2099-01-01T00:00:00+00:00",exact_job_seconds=600,remote_job_seconds=600,
             maximum_native_chi=512,baseline_quote_reserve_usd_per_row=.2,
             pilot_qubits={p:[0] for p in ("G1","G2","G3","G4")},
             graded_policy={p:{"primary":"cpu" if p=="G1" else "pauli-path" if p=="G3" else "mps.cpu",
                               "fallback":"mps.cpu","chi":256,"epsilon":.001,"reason":"sample evidence"}
                            for p in ("G1","G2","G3","G4")})
    return s


def record(cid,device,options,value=.4,status="COMPLETED"):
    return {"action":{"circuit_id":cid,"device":device,"options":options},"status":status,
            "estimate":value,"cost_usd":0.,"job_id":"test"}


class GradedTests(TestCase):
    def test_selected_cohort_quotes_raise_future_coverage_reserve(self):
        with TemporaryDirectory() as folder, patch('otoc.graded.event'):
            r=record('Duke_G2_0','mps.cpu',{'mps_bond_dimension':256})
            r['quote']={'cost_usd':3.02}
            class Adapter:
                root=Path(folder)
                def usage(self):
                    return {'known_cost_usd':0.,'active_jobs':0,'unknown_terminal_costs':0,'job_count':0}
                def quote(self,cid,device,options):
                    return {'cost_usd':.2,'runtime_seconds':30.,'error':None}
            with patch('otoc.graded.action_history',return_value=[r]):
                plan=plan_next(Adapter(),settings(),['G2'],1)
            self.assertEqual(plan['baseline_quote_rates']['G2'],3.02)
            self.assertIsNone(plan['next'])
            self.assertEqual(plan['actions'][0]['gate'],'protect_remaining_baseline_budget')

    def test_fallback_rows_do_not_satisfy_selected_cohort_coverage(self):
        s=settings()
        rows=[record('Duke_G3_0','mps.cpu',{'mps_bond_dimension':16})]
        actions=candidates_for('G3',rows,s)
        self.assertTrue(any(a['circuit_id']=='Duke_G3_0' and a['device']=='pauli-path' and a['stage']=='coverage' for a in actions))

    def test_discovery_survives_recovery_to_mps(self):
        s=settings();s['discovery']={'enabled':True,'pps_transpilation_level':1,'mps_chi':32}
        s['pilot_qubits']['G2']=[0,18,35]
        rows=[record('Duke_G2_0','pauli-path',{'pauli_path_truncation_threshold':.001,'pauli_path_circuit_transpilation_level':2},0.),
              record('Duke_G2_0','mps.cpu',{'mps_bond_dimension':256},.4)]
        actions=candidates_for('G2',rows,s)
        self.assertTrue(any(a['stage']=='discovery' and a['device']=='pauli-path' and
                            a['options']['pauli_path_circuit_transpilation_level']==1 for a in actions))

    def test_selection_uses_precision_and_exactness_not_file_order(self):
        rows=[record("Duke_G2_0","mps.cpu",{"mps_bond_dimension":256},.8),
              record("Duke_G2_0","mps.cpu",{"mps_bond_dimension":8},.1)]
        self.assertEqual(select_record(rows,"G2",settings())[0]["estimate"],.8)
        rows.append(record("Duke_G2_0","cpu",{},.6))
        self.assertEqual(select_record(rows,"G2",settings())[0]["estimate"],.6)

    def test_failed_action_is_not_silently_resubmitted(self):
        failed=record("Duke_G2_0","mps.cpu",{"mps_bond_dimension":256},None,"TERMINATED")
        self.assertFalse(any(a["circuit_id"]=="Duke_G2_0" and a["device"]=="mps.cpu"
                             for a in candidates_for("G2",[failed],settings())))

    def test_flat_pilot_blocks_bulk_coverage_but_allows_refinement(self):
        s=settings()
        s["pilot_signal_gate"]=True
        s["pilot_qubits"]["G3"]=[0,14,35]
        rows=[record(f"Duke_G3_{q}","pauli-path",{"pauli_path_truncation_threshold":.001,
                     "pauli_path_circuit_transpilation_level":2},0.) for q in (0,14,35)]
        actions=candidates_for("G3",rows,s)
        self.assertTrue(actions)
        self.assertTrue(all(int(a["circuit_id"].split("_")[-1]) in (0,14,35) for a in actions))
        self.assertTrue(any(a["stage"]=="refine" for a in actions))

    def test_changed_prices_protect_baseline_and_exact_has_fallback(self):
        with TemporaryDirectory() as folder, patch("otoc.graded.event"):
            class Adapter:
                root=Path(folder)
                def usage(self):
                    return {"known_cost_usd":0.,"active_jobs":0,"unknown_terminal_costs":0,"job_count":0}
                def quote(self,cid,device,options):
                    return {"cost_usd":1. if device=="cpu" else 10.,"runtime_seconds":30.,"error":None}
            plan=plan_next(Adapter(),settings(),["G1"],1)
            self.assertIsNone(plan["next"])
            self.assertEqual(plan["actions"][0]["device"],"mps.cpu")
            self.assertEqual(plan["actions"][0]["gate"],"protect_remaining_baseline_budget")

    def test_ambiguous_submission_never_calls_run_again(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            action={"circuit_id":"Duke_S1_0","device":"cpu","options":{},"pauli":"IIIZ"}
            path=root/"remote_actions"/(digest(action)+".json")
            path.parent.mkdir()
            path.write_text(json.dumps({"action":action,"status":"SUBMITTING"}))
            class Client:
                def run(self,*args,**kwargs):
                    raise AssertionError("Duplicate submission")
            with self.assertRaisesRegex(RuntimeError,"uncertain status"):
                BlueQubitAdapter(root,Client()).run("Duke_S1_0","cpu",{},settings())

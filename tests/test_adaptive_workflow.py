import unittest
from otoc.adaptive import stopping_diagnostic, vector_comparison
from otoc.bluequbit_adapter import cost_gate, validate_action
from otoc.calibration import load_settings


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.config=load_settings()
        self.stop=self.config["stopping"]
        self.usage={"known_cost_usd":0,"job_count":0,"unknown_terminal_costs":0,"active_jobs":0}

    def test_cross_agreement_alone_does_not_stop(self):
        result=stopping_diagnostic([0.4],[0.4],1,self.stop,0,True)
        self.assertFalse(result["stop"])

    def test_two_recent_steps_and_cross_disagreement_must_all_be_small(self):
        stable=stopping_diagnostic([0.4,0.4001,0.4002],[0.4003,0.4002,0.4001],1,self.stop,0,True)
        self.assertTrue(stable["stop"])
        unstable=stopping_diagnostic([0.8,0.4,0.4002],[0.4,0.4,0.4002],1,self.stop,0,True)
        self.assertFalse(unstable["stop"])

    def test_constant_vectors_do_not_certify_shape(self):
        shape=vector_comparison([0,0,0],[0,0,0])
        self.assertFalse(shape["signal_resolved"])
        self.assertIsNone(shape["shape_change"])

    def test_sample_charge_and_unknown_cost_blocked(self):
        for cost in (0.2,None):
            self.assertFalse(cost_gate("S3",{"cost_usd":cost},self.usage,self.config)[0])
        self.assertTrue(cost_gate("S3",{"cost_usd":0},self.usage,self.config)[0])

    def test_graded_budget_preserves_reserve(self):
        self.assertFalse(cost_gate("G4",{"cost_usd":0.2},self.usage,self.config)[0])
        used=dict(self.usage,known_cost_usd=25.4)
        self.assertFalse(cost_gate("G4",{"cost_usd":0.2},used,self.config,"refine unstable target")[0])

    def test_active_or_unaccounted_jobs_prevent_submission(self):
        for field in ("active_jobs","unknown_terminal_costs"):
            usage=dict(self.usage,**{field:1})
            self.assertFalse(cost_gate("S1",{"cost_usd":0},usage,self.config)[0])

    def test_id_and_pps_validation(self):
        problem,label=validate_action("Duke_S2_5","cpu",{})
        self.assertEqual((problem,label),("S2","I"*10+"Z"+"I"*5))
        with self.assertRaises(ValueError):
            validate_action("Duke_G4_38","cpu",{})
        with self.assertRaises(ValueError):
            validate_action("Duke_G3_0","pauli-path",{"pauli_path_truncation_threshold":1e-6})


if __name__=="__main__":
    unittest.main()

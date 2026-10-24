from unittest import TestCase
from otoc.adaptive import trend_diagnostic
from otoc.bluequbit_adapter import cost_gate
from otoc.calibration import load_settings
from otoc.graded import select_record, candidates_for


class TrendGpuTests(TestCase):
    def test_monotone_contraction_is_not_extrapolated_into_an_answer(self):
        trend=trend_diagnostic([.2,.3,.35,.375],[8,16,32,64])
        self.assertEqual(trend["classification"],"CONTRACTING")
        self.assertAlmostEqual(trend["last_contraction_ratio"],.5)
        self.assertNotIn("estimate",trend)

    def test_oscillation_and_false_flatness_are_visible(self):
        oscillating=trend_diagnostic([.1,.3,.15,.25],[8,16,32,64])
        self.assertEqual(oscillating["classification"],"OSCILLATING")
        self.assertGreater(oscillating["sign_flips"],0)
        self.assertEqual(trend_diagnostic([0,0,0],[.01,.001,.0001])["classification"],"FLAT_UNVERIFIED")

    def test_gpu_quota_blocks_even_when_dollars_fit(self):
        s=load_settings()
        usage={"known_cost_usd":0,"job_count":0,"active_jobs":0,"gpu_time_known":True,
               "gpu_seconds":1000,"gpu_seconds_last_hour":2650}
        quote={"device":"mps.gpu","cost_usd":.2,"runtime_seconds":100}
        self.assertEqual(cost_gate("G2",quote,usage,s,"Native check")[1],"gpu_rolling_hour_quota")
        usage["gpu_seconds_last_hour"]=0
        self.assertTrue(cost_gate("G2",quote,usage,s,"Native check")[0])

    def test_exact_gpu_precedes_approximation(self):
        s={"graded_policy":{"G2":{"primary":"pauli-path"}}}
        rows=[{"status":"COMPLETED","estimate":.2,"cost_usd":0,"action":{"device":"pauli-path","options":{"pauli_path_truncation_threshold":.001}}},
              {"status":"COMPLETED","estimate":.3,"cost_usd":0,"action":{"device":"gpu","options":{}}}]
        self.assertEqual(select_record(rows,"G2",s)[0]["estimate"],.3)

    def test_gpu_result_does_not_trigger_repeated_same_precision_cpu_work(self):
        s=load_settings()
        s.update(graded_policy={"G3":{"primary":"pauli-path","epsilon":.001,"chi":16,"reason":"test"}},
                 pilot_qubits={"G3":[0]},maximum_native_chi=512)
        rows=[{"status":"COMPLETED","estimate":.2,"cost_usd":.2,
               "action":{"circuit_id":"Duke_G3_0","device":"pauli-path.gpu",
                         "options":{"pauli_path_truncation_threshold":.001,"pauli_path_circuit_transpilation_level":2}}},
              {"status":"COMPLETED","estimate":.21,"cost_usd":.2,
               "action":{"circuit_id":"Duke_G3_0","device":"mps.gpu","options":{"mps_bond_dimension":16}}}]
        proposals=[a for a in candidates_for("G3",rows,s) if a["circuit_id"]=="Duke_G3_0"]
        self.assertTrue(proposals)
        self.assertTrue(all(a["stage"]=="refine" for a in proposals))

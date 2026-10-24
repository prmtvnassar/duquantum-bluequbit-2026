from collections import defaultdict
from types import SimpleNamespace
from unittest import TestCase
import numpy as np
from otoc.calibration import load_settings
from otoc.tuning import replay_stopping


class StoppingReplayTests(TestCase):
    def test_early_shared_bias_is_detected_even_when_final_answers_are_exact(self):
        group=[SimpleNamespace(circuit_id=f"Duke_S1_{q}") for q in range(2)]
        truth=np.array([0.,1.])
        history=defaultdict(list)
        for q,sample in enumerate(group):
            for method,levels in (("mps",[1,2,4,8,16,32]),("pps_threshold",[.01,.003,.001,.0003,.0001,.00003])):
                for i,level in enumerate(levels):
                    history[(sample.circuit_id,method)].append({
                        "parameters":{"chi":level} if method=="mps" else {"epsilon":level,"level":1},
                        "estimate":truth[q]+(.05 if i<3 else 0.)})
        result=replay_stopping(group,history,truth,load_settings()["stopping"])
        self.assertGreaterEqual(result["false_stops"],2)
        self.assertEqual(result["prefixes"][-1]["false_stops"],0)
        self.assertEqual(result["prefixes"][-1]["stopped_count"],2)

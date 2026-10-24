import unittest
from otoc.campaign_reasoning import shape_influence, empirical_seconds, recover_flat_policy, complete_vector_trends


class CampaignReasoningTests(unittest.TestCase):
    def test_vector_trends_require_complete_vectors_and_fixed_transpilation(self):
        rows=[]
        for eps,level,values in [(.01,2,[0.,.2,.8]),(.001,1,[0.,.3,.7])]:
            for q,v in enumerate(values):
                rows.append({'action':{'circuit_id':f'Duke_G2_{q}','device':'pauli-path',
                            'options':{'pauli_path_truncation_threshold':eps,'pauli_path_circuit_transpilation_level':level}},
                            'status':'COMPLETED','estimate':v,'cost_usd':0.})
        self.assertFalse(complete_vector_trends(rows,{'G2':3}))
        for row in rows[3:]:
            row['action']['options']['pauli_path_circuit_transpilation_level']=2
        self.assertFalse(complete_vector_trends(rows[:-1],{'G2':3}))
        self.assertIn('G2/pauli-path/2',complete_vector_trends(rows,{'G2':3}))

    def test_affine_change_has_no_shape_influence(self):
        r=shape_influence([-.5,0,.2,.9],[0,1,1.4,2.8])
        self.assertLess(r['relative_shape_residual'],1e-25)
        self.assertAlmostEqual(r['shape_change'],0)
        self.assertEqual(shape_influence([0,0,0],[.1,.2,.3])['status'],'NEAR_CONSTANT_VECTOR')
        self.assertEqual(shape_influence([0,1,2],[2,1,0])['status'],'SIGN_REVERSAL')

    def test_empirical_runtime_never_discounts_quote(self):
        a={'problem':'G2','device':'pauli-path'}
        r={'action':{'circuit_id':'Duke_G2_0','device':'pauli-path'},'status':'COMPLETED',
           'estimate':0.,'cost_usd':0.,'requested_at':'2026-10-24T12:00:00+00:00',
           'updated_at':'2026-10-24T12:04:00+00:00'}
        self.assertEqual(empirical_seconds(a,[r],.1)['seconds'],240)
        self.assertEqual(empirical_seconds(a,[r],500)['seconds'],500)

    def test_recovery_requires_complete_identical_precision_pilot(self):
        s={'graded_policy':{'G2':{'primary':'pauli-path'}},'pilot_qubits':{'G2':[0,1,2]},
           'stopping':{'signal_floor':.0001}}
        def row(q,device,value,options):
            return {'action':{'circuit_id':f'Duke_G2_{q}','device':device,'options':options},
                    'status':'COMPLETED','estimate':value,'cost_usd':0.,'job_id':str(q)}
        rows=[row(q,'pauli-path',0.,{'pauli_path_truncation_threshold':.001}) for q in range(3)]
        rows += [row(q,'mps.cpu',q/3,{'mps_bond_dimension':16}) for q in range(2)]
        self.assertFalse(recover_flat_policy(s,rows)[1])
        rows.append(row(2,'mps.cpu',.7,{'mps_bond_dimension':32}))
        self.assertFalse(recover_flat_policy(s,rows)[1])
        rows.append(row(2,'mps.cpu',.7,{'mps_bond_dimension':16}))
        settings,evidence=recover_flat_policy(s,rows)
        self.assertEqual(settings['graded_policy']['G2']['primary'],'mps.cpu')
        self.assertEqual(s['graded_policy']['G2']['primary'],'pauli-path')
        self.assertIn('G2',evidence)

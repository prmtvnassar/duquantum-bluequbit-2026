from copy import deepcopy
import unittest
from otoc.campaign_reasoning import shape_influence, empirical_seconds, recover_flat_policy, complete_vector_trends


class CampaignReasoningTests(unittest.TestCase):
    @staticmethod
    def recovery_settings(primary='pauli-path'):
        return {'graded_policy':{'G3':{'primary':primary,'epsilon':.001}},
                'pilot_qubits':{'G3':[0,1,2]},'cloud_pps_transpilation_level':2,
                'stopping':{'signal_floor':.0001}}

    @staticmethod
    def pilot_rows(device,options,values):
        return [{'action':{'circuit_id':f'Duke_G3_{q}','device':device,'options':deepcopy(options)},
                 'status':'COMPLETED','estimate':value,'cost_usd':0.,'job_id':f'{device}-{q}'}
                for q,value in enumerate(values)]

    def test_recovery_never_combines_cpu_and_gpu_pilots(self):
        s=self.recovery_settings()
        flat=self.pilot_rows('pauli-path',{'pauli_path_truncation_threshold':.001},[0,0,0])
        cpu=self.pilot_rows('mps.cpu',{'mps_bond_dimension':16},[.1,.2,.3])
        gpu=self.pilot_rows('mps.gpu',{'mps_bond_dimension':16},[.1,.2,.3])
        _,evidence=recover_flat_policy(s,flat+cpu[:2]+gpu[2:])
        self.assertFalse(evidence)
        selected,evidence=recover_flat_policy(s,flat+gpu)
        self.assertEqual(selected['graded_policy']['G3']['primary'],'mps.gpu')
        self.assertEqual(evidence['G3']['configuration'],{'device':'mps.gpu','options':{'mps_bond_dimension':16}})

    def test_recovery_preserves_all_options_and_does_not_combine_variants(self):
        s=self.recovery_settings()
        flat=self.pilot_rows('pauli-path',{'pauli_path_truncation_threshold':.001},[0,0,0])
        options={'mps_bond_dimension':16,'cutoff':0.0,'backend_options':{'mode':'preserved'}}
        rows=self.pilot_rows('mps.cpu',options,[.1,.2,.3])
        other=deepcopy(rows[-1])
        other['action']['options']['cutoff']=.001
        self.assertFalse(recover_flat_policy(s,flat+rows[:2]+[other])[1])
        selected,evidence=recover_flat_policy(s,flat+rows)
        self.assertEqual(selected['graded_policy']['G3']['baseline_options'],options)
        selected['graded_policy']['G3']['baseline_options']['backend_options']['mode']='changed'
        self.assertEqual(rows[0]['action']['options'],options)
        self.assertEqual(evidence['G3']['options'],options)

    def test_finer_resolved_original_configuration_replaces_flat_coarse(self):
        s=self.recovery_settings()
        coarse={'pauli_path_truncation_threshold':.001,'pauli_path_circuit_transpilation_level':2}
        fine={'pauli_path_truncation_threshold':.0001,'pauli_path_circuit_transpilation_level':2}
        rows=self.pilot_rows('pauli-path',coarse,[0,0,0])
        rows+=self.pilot_rows('pauli-path',fine,[-.02,0,-.01])
        selected,evidence=recover_flat_policy(s,rows)
        self.assertEqual(selected['graded_policy']['G3']['epsilon'],.0001)
        self.assertEqual(selected['graded_policy']['G3']['baseline_options'],fine)
        self.assertEqual(evidence['G3']['options'],fine)
        self.assertEqual(s['graded_policy']['G3']['epsilon'],.001)

    def test_resolved_pilots_are_ranked_by_precision_not_amplitude(self):
        s=self.recovery_settings()
        coarse={'pauli_path_truncation_threshold':.001,'pauli_path_circuit_transpilation_level':2}
        fine={'pauli_path_truncation_threshold':.0001,'pauli_path_circuit_transpilation_level':1}
        rows=self.pilot_rows('pauli-path',coarse,[-.9,0,.9])
        rows+=self.pilot_rows('pauli-path',fine,[-.002,0,.001])
        rows+=self.pilot_rows('mps.cpu',{'mps_bond_dimension':512},[-1,0,1])
        selected,evidence=recover_flat_policy(s,list(reversed(rows)))
        self.assertEqual(selected['graded_policy']['G3']['primary'],'pauli-path')
        self.assertEqual(selected['graded_policy']['G3']['baseline_options'],fine)
        self.assertAlmostEqual(evidence['G3']['pilot_spread'],.003)

    def test_original_family_preference_survives_repeated_recovery(self):
        s=self.recovery_settings()
        coarse={'pauli_path_truncation_threshold':.001,'pauli_path_circuit_transpilation_level':2}
        level1={'pauli_path_truncation_threshold':.001,'pauli_path_circuit_transpilation_level':1}
        rows=self.pilot_rows('pauli-path',coarse,[0,0,0])
        rows+=self.pilot_rows('mps.cpu',{'mps_bond_dimension':16},[.1,.2,.3])
        switched,_=recover_flat_policy(s,rows)
        self.assertEqual(switched['graded_policy']['G3']['primary'],'mps.cpu')
        selected,_=recover_flat_policy(switched,rows+self.pilot_rows('pauli-path',level1,[-.02,0,-.01]))
        self.assertEqual(selected['graded_policy']['G3']['primary'],'pauli-path')
        self.assertEqual(selected['graded_policy']['G3']['baseline_options'],level1)

    def test_resolved_same_family_representation_precedes_cross_family_recovery(self):
        s={'graded_policy':{'G3':{'primary':'pauli-path'}},'pilot_qubits':{'G3':[0,1,2]},
           'cloud_pps_transpilation_level':2,'stopping':{'signal_floor':.0001}}
        rows=[]
        for level,vals in [(2,[0,0,0]),(1,[-.07,0,-.03])]:
            for q,v in enumerate(vals):
                rows.append({'action':{'circuit_id':f'Duke_G3_{q}','device':'pauli-path',
                             'options':{'pauli_path_truncation_threshold':.001,'pauli_path_circuit_transpilation_level':level}},
                             'status':'COMPLETED','estimate':v,'cost_usd':0.,'job_id':str(q)})
        selected,evidence=recover_flat_policy(s,rows)
        self.assertEqual(selected['graded_policy']['G3']['transpilation_level'],1)
        self.assertIn('G3',evidence)

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

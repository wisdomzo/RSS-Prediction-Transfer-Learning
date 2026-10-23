import unittest
import ast
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import pandas as pd
from sampling_suggestions import METHODS, UNCERTAINTY_METHODS, generate_suggestions
from sampling_kernels import spacing_schedule


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{'Latitude': 36+i*.0001, 'Longitude': 138+(i%4)*.0001,
                      'Uncertainty': i/40, 'SampleID': f'original-{i}', 'RSSI': -999}
                     for i in range(40)]
        self.options = dict(budget_mode='count', budget=6, min_samples=2,
                            start_lat=36, start_lon=138)

    def test_all_methods_deduplicate_before_budget_and_preserve_fields(self):
        for method in METHODS:
            with self.subTest(method=method):
                result = generate_suggestions(self.rows + [self.rows[0]], dict(self.options, method=method))
                self.assertEqual(result['removed_duplicates'], 1)
                self.assertEqual(result['candidate_count'], 40)
                self.assertEqual(result['selected_count'], 6)
                points = result['records']
                self.assertEqual(len({(p['Latitude'], p['Longitude']) for p in points}), 6)
                self.assertTrue(all(p['SampleID'].startswith('original-') for p in points))
                self.assertEqual([p['Sampling_Order'] for p in points], list(range(1, 7)))
                self.assertEqual(result, generate_suggestions(self.rows + [self.rows[0]], dict(self.options, method=method)))

    def test_labels_do_not_affect_selection(self):
        changed = [dict(p, RSSI=100*i, Predicted_Value=-i, Model_0=i) for i,p in enumerate(self.rows)]
        for method in METHODS:
            with self.subTest(method=method):
                before = generate_suggestions(self.rows, dict(self.options, method=method))
                after = generate_suggestions(changed, dict(self.options, method=method))
                self.assertEqual([r['SampleID'] for r in before['records']], [r['SampleID'] for r in after['records']])

    def test_percentage_uses_unique_count_and_first_record(self):
        rows = self.rows + [dict(self.rows[0], Uncertainty=999)]
        result = generate_suggestions(rows, dict(method='top_u', budget=10))
        self.assertEqual(result['selected_count'], 4)
        self.assertEqual(result['records'][0]['SampleID'], 'original-39')

    def test_spatial_methods_do_not_require_uncertainty_or_rssi(self):
        rows = [{k:v for k,v in p.items() if k not in {'RSSI','Uncertainty'}} for p in self.rows]
        for method in METHODS - UNCERTAINTY_METHODS:
            self.assertEqual(generate_suggestions(rows, dict(self.options, method=method))['selected_count'], 6)
        with self.assertRaisesRegex(ValueError, 'Uncertainty'):
            generate_suggestions(rows, self.options)

    def test_spacing_and_full_budget(self):
        self.assertEqual(spacing_schedule(25), [25,15,None])
        self.assertEqual(spacing_schedule(30), [30,20,10,None])
        self.assertEqual(spacing_schedule(9), [None])
        for method in ('uras_spatial', 'uras_spatial_no_u'):
            result = generate_suggestions(self.rows, dict(self.options, method=method, budget=40, initial_spacing=25))
            self.assertEqual([r['spacing_m'] for r in result['rounds']], [25,15,None])
            self.assertEqual(sum(r['added'] for r in result['rounds']),40)

    def test_invalid_parameters(self):
        for override in [dict(budget=0), dict(budget=41), dict(budget=1.5),
                         dict(initial_spacing=-1), dict(eps=0), dict(seed=-1),
                         dict(min_samples=1.5), dict(method='unknown')]:
            with self.subTest(override=override), self.assertRaises(ValueError):
                generate_suggestions(self.rows, {**self.options, **override})

    def test_native_csv_export_and_cancel(self):
        source = Path(__file__).resolve().parents[1] / 'main.py'
        api = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'Api')
        method = next(n for n in api.body if isinstance(n, ast.FunctionDef) and n.name == 'download_sampling_suggestions')
        namespace = {'pd': pd, 'webview': SimpleNamespace(FileDialog=SimpleNamespace(SAVE='save'))}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'suggestions.csv'
            namespace['window'] = SimpleNamespace(create_file_dialog=lambda *a, **kw: [str(path)])
            records = generate_suggestions(self.rows, self.options)['records']
            self.assertEqual(namespace['download_sampling_suggestions'](None, records)['status'], 'ok')
            saved = pd.read_csv(path)
            self.assertEqual(len(saved), 6)
            self.assertEqual(saved.Sampling_Order.tolist(), list(range(1,7)))
            namespace['window'] = SimpleNamespace(create_file_dialog=lambda *a, **kw: None)
            self.assertEqual(namespace['download_sampling_suggestions'](None, records)['status'], 'cancelled')


if __name__ == '__main__':
    unittest.main()

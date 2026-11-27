import unittest
from unittest.mock import Mock, patch
from app import app
from tracker import totals


class TrackerTest(unittest.TestCase):
    def test_estimate_before_save(self):
        client = app.test_client()
        self.assertEqual(client.get('/tracker').status_code, 401)
        with client.session_transaction() as state:
            state.update(user_id=12, csrf_token='token')
        query = Mock()
        query.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(), query)), patch('tracker.genai.Client') as ai:
            ai.return_value.__enter__.return_value.models.generate_content.return_value.text = '{"portion":"1 cup rice, 1 chicken piece, 1 glass Milo","kcal":700,"protein_g":25,"carbs_g":90,"fat_g":20}'
            data = dict(action='estimate', token='token', meal_name='nasi putih, kari ayam, air milo')
            response = client.post('/tracker', data=data)
            self.assertIn(b'Review AI estimate', response.data)
            self.assertIn(b'700', response.data)
            self.assertFalse(any('INSERT' in call.args[0] for call in query.call_args_list))
            ai.return_value.__enter__.return_value.models.generate_content.return_value.text = '{}'
            failed = client.post('/tracker', data=dict(data, date='2026-11-01', meal_portion='one plate'))
            self.assertEqual(failed.status_code, 502)
            self.assertIn(b'value="nasi putih, kari ayam, air milo"', failed.data)
            self.assertIn(b'value="one plate"', failed.data)
            self.assertIn(b'2026-11-01', failed.data)
            self.assertIn(b'role="alert"', failed.data)
            self.assertEqual(client.post('/tracker', data=dict(data, token='bad')).status_code, 403)

    def test_totals(self):
        self.assertEqual(totals([dict(kcal=100, protein_g=2, carbs_g=20, fat_g=1)]), [100, 2, 20, 1])

    def test_custom_meal(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=12, csrf_token='token')
        query = Mock()
        query.return_value.fetchall.return_value = []
        data = dict(action='save_custom', token='token', meal_name='nasi putih, kari ayam, air milo',
                    meal_portion='1 cup, 1 piece, 1 glass', kcal='700', protein_g='25', carbs_g='90', fat_g='20')
        with patch.dict(app.extensions, planner_db=(Mock(), query)):
            self.assertEqual(client.post('/tracker', data=data).status_code, 303)
            self.assertEqual(query.call_args.args[1][0], 12)
            self.assertEqual(query.call_args.args[1][2], data['meal_name'])
            self.assertEqual(client.post('/tracker', data=dict(data, kcal='nan')).status_code, 400)

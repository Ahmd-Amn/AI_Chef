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
            self.assertIn(b'>nasi putih, kari ayam, air milo</textarea>', failed.data)
            self.assertIn(b'>one plate</textarea>', failed.data)
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

    def test_estimate_uses_backup_when_primary_unavailable(self):
        from google.genai.errors import ServerError
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=1, csrf_token='token')
        query = Mock()
        query.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(), query)), patch('tracker.genai.Client') as ai:
            generate = ai.return_value.__enter__.return_value.models.generate_content
            from tracker import TimeoutException, NetworkError
            failures = [ServerError(code, {'error': {'message': 'unavailable'}}) for code in (500, 502, 503, 504)]
            failures.extend([TimeoutException('timeout'), NetworkError('network unavailable')])
            for failure in failures:
                with self.subTest(failure=type(failure).__name__, code=getattr(failure, 'code', None)):
                    generate.reset_mock()
                    generate.side_effect = [failure, Mock(text='{"portion":"1 cup rice","kcal":200,"protein_g":4,"carbs_g":45,"fat_g":1}')]
                    response = client.post('/tracker', data=dict(action='estimate', token='token', meal_name='rice'))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual([call.kwargs['model'] for call in generate.call_args_list],
                                     ['gemini-3.8-flash', 'gemini-3.5-flash-lite'])
            generate.reset_mock()
            generate.side_effect = [ServerError(504, {'error': {'message': 'timeout'}}),
                                    ServerError(503, {'error': {'message': 'busy'}})]
            response = client.post('/tracker', data=dict(action='estimate', token='token', meal_name='rice'))
            self.assertEqual(response.status_code, 502)
            self.assertEqual(generate.call_count, 2)
            self.assertIn(b'>rice</textarea>', response.data)

    def test_food_only_drinks_only_and_combined(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=1, csrf_token='token')
        query = Mock()
        query.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(), query)), patch('tracker.genai.Client') as ai:
            ai.return_value.__enter__.return_value.models.generate_content.return_value.text = '{"portion":"1 serving","kcal":100,"protein_g":1,"carbs_g":20,"fat_g":2}'
            for items in ('nasi putih', 'air milo', 'nasi putih\nair milo'):
                with self.subTest(items=items):
                    response = client.post('/tracker', data=dict(action='estimate', token='token', meal_name=items))
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b'Review your estimate', response.data)

    def test_saved_popup_only_after_successful_save(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=1, csrf_token='token')
        query = Mock()
        query.return_value.fetchall.return_value = []
        db = Mock()
        query.return_value.lastrowid = 42
        with patch.dict(app.extensions, planner_db=(db, query)):
            response = client.post('/tracker', follow_redirects=True, data=dict(
                action='save_custom', token='token', meal_name='rice', meal_portion='1 cup',
                kcal=200, protein_g=4, carbs_g=45, fat_g=1))
            self.assertEqual(response.status_code, 200)
            self.assertIn('#food-log-42', response.history[0].headers['Location'])
            self.assertIn(b'id="savedPopup"', response.data)
            self.assertIn(b'>Saved</h2>', response.data)
            db.return_value.commit.assert_called_once()
            self.assertNotIn(b'id="savedPopup"', client.get('/tracker').data)

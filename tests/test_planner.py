import unittest
from unittest.mock import Mock, patch

from app import app
from planner import eligible, assemble_plan, MEALS


class PlannerTest(unittest.TestCase):
    def test_exclusions(self):
        self.assertEqual(eligible('Breakfast', 'gluten'), ['apple_rice'])
        self.assertNotIn('peas', eligible('Dinner', 'WHEAT'))

    def test_generate_swap_save(self):
        client = app.test_client()
        self.assertEqual(client.get('/planner').status_code, 401)
        with client.session_transaction() as state:
            state.update(user_id=9, csrf_token='token')
        sql = Mock()
        sql.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(), sql)), patch('planner.genai.Client') as ai:
            ai.return_value.__enter__.return_value.models.generate_content.return_value.text = '["berry_oats","beans","lentils"]'
            params = dict(action='generate', goal='Maintain weight', days='1')
            self.assertEqual(client.post('/planner', data=params).status_code, 403)
            response = client.post('/planner', data=dict(params, token='token'), follow_redirects=True)
            self.assertIn(b'Day total', response.data)
            ai.assert_not_called()
            response = client.post('/planner', data=dict(action='swap', index=0, token='token'), follow_redirects=True)
            self.assertIn(b'Apple cinnamon rice', response.data)
            self.assertEqual(client.post('/planner', data=dict(action='save', token='token')).status_code, 303)
            self.assertEqual(sql.call_args.args[1][0], 9)

    def test_calorie_target_and_weights(self):
        choices = {'Breakfast': ['berry_oats', 'apple_rice'], 'Lunch': ['beans', 'lentils']}
        plan = assemble_plan(choices, 1, 'Maintain weight', 845)
        self.assertEqual(sum(MEALS[key][3][0] for key in plan), 845)
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=9, csrf_token='token')
        sql = Mock()
        sql.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(), sql)):
            data = dict(action='generate', goal='Fat loss', days='1', token='token')
            self.assertEqual(client.post('/planner', data=data).status_code, 400)
            for calories in ('nan', '-1', 'inf'):
                self.assertEqual(client.post('/planner', data=dict(data, current_weight=80, target_weight=70, calories=calories)).status_code, 400)
            self.assertEqual(client.post('/planner', data=dict(data, current_weight=80, target_weight=70, calories=1800)).status_code, 303)
            with client.session_transaction() as state:
                self.assertEqual(state['meal_draft']['current_weight'], 80)
                self.assertEqual(state['meal_draft']['calories'], 1800)

    def test_settings_survive_redirect_and_validation(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=9, csrf_token='token')
        sql = Mock()
        sql.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(), sql)):
            data = dict(action='generate', token='token', days='7', goal='Fat loss',
                        current_weight='80', target_weight='70', exclude='wheat')
            response = client.post('/planner', data=data, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'value="7" selected', response.data)
            self.assertIn(b'value="80"', response.data)
            self.assertIn(b'<details', response.data)
            self.assertIn(b'authBtn', response.data)
            self.assertIn(b'/?library=history', response.data)
            response = client.post('/planner', data=dict(data, target_weight='90'))
            self.assertEqual(response.status_code, 400)
            self.assertIn(b'value="90"', response.data)
            self.assertIn(b'role="alert"', response.data)

import unittest
from unittest.mock import Mock, patch
import pymysql
from app import app
from feedback import AI_ERROR, form_errors


class FeedbackTest(unittest.TestCase):
    def test_weight_error_points_to_target(self):
        with app.test_request_context('/planner', method='POST', data=dict(action='generate', days='7',
                                     goal='Fat loss', current_weight='80', target_weight='90')):
            self.assertIn('target_weight', form_errors())

    def test_tracker_errors_and_ai_outage_preserve_input(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=1, csrf_token='test')
        sql = Mock()
        sql.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(), sql)):
            response = client.post('/tracker', data=dict(action='save_custom', token='test',
                                   meal_name='rice', meal_portion='1 cup', kcal='nan'))
            self.assertEqual(response.status_code, 400)
            self.assertIn(b'fieldErrors', response.data)
            self.assertIn(b'kcal', response.data)
            with patch('tracker.genai.Client', side_effect=RuntimeError('outage')):
                response = client.post('/tracker', data=dict(action='estimate', token='test', meal_name='rice'))
            self.assertEqual(response.status_code, 502)
            self.assertIn(AI_ERROR.encode(), response.data)
            self.assertIn(b'value="rice"', response.data)

    def test_database_error_is_service_message(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=1, csrf_token='test')
        with patch('app.query', side_effect=pymysql.OperationalError(2003, 'connection failed')):
            response = client.get('/api/recipes')
        self.assertEqual(response.status_code, 503)
        self.assertIn('No services', response.json['error'])

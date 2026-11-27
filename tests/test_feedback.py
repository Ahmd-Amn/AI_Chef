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
            self.assertIn(b'>rice</textarea>', response.data)

    def test_database_error_is_service_message(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=1, csrf_token='test')
        with patch('app.query', side_effect=pymysql.OperationalError(2003, 'connection failed')):
            response = client.get('/api/recipes')
        self.assertEqual(response.status_code, 503)
        self.assertIn('No services', response.json['error'])

    def test_recipe_and_tracker_rate_limit_messages(self):
        from google.genai.errors import ClientError
        from feedback import AI_RATE_ERROR
        client = app.test_client()
        with client.session_transaction() as state:
            state['csrf_token']='token'
        with patch('app.genai.Client') as ai:
            generate=ai.return_value.__enter__.return_value.models.generate_content
            generate.side_effect=ClientError(429,{'error':{'message':'quota'}})
            response=client.post('/api/recipe',json={'ingredients':'rice'},headers={'X-CSRF-Token':'token'})
            self.assertEqual(response.status_code,429)
            self.assertEqual(response.json['error'],AI_RATE_ERROR)
            self.assertNotIn('retry_after',response.json)
            self.assertEqual(generate.call_count,2)
        with client.session_transaction() as state:
            state['user_id']=1
        query=Mock()
        query.return_value.fetchall.return_value=[]
        with patch.dict(app.extensions,planner_db=(Mock(),query)),patch('tracker.genai.Client') as ai:
            generate=ai.return_value.__enter__.return_value.models.generate_content
            generate.side_effect=ClientError(429,{'error':{'message':'quota'}})
            response=client.post('/tracker',data=dict(action='estimate',token='token',meal_name='air milo'))
            self.assertEqual(response.status_code,429)
            self.assertIn(AI_RATE_ERROR.encode(),response.data)
            self.assertIn(b'>air milo</textarea>',response.data)
            self.assertEqual(generate.call_count,2)

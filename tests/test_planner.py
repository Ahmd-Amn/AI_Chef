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
        sql.return_value.lastrowid = 1
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
        sql.return_value.lastrowid = 1
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
        sql.return_value.lastrowid = 1
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

    def test_multilingual_exclusions(self):
        from planner import translate_exclusions
        with patch('planner.genai.Client') as ai:
            ai.return_value.__enter__.return_value.models.generate_content.return_value.text = '["wheat", "oats"]'
            translated = translate_exclusions('tepung gandum\n燕麦')
            self.assertNotIn('peas', eligible('Dinner', translated))
            self.assertEqual(eligible('Breakfast', translated), ['apple_rice'])
            ai.return_value.__enter__.return_value.models.generate_content.return_value.text = '[]'
            with self.assertRaises(ValueError):
                translate_exclusions('unknown ingredient')

    def test_exclusion_timeout_fallback_and_result_navigation(self):
        from google.genai.errors import ServerError
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=9, csrf_token='token')
        sql = Mock()
        sql.return_value.fetchall.return_value = []
        sql.return_value.lastrowid = 1
        data = dict(action='generate',token='token',days='1',goal='Maintain weight',exclude='tepung gandum')
        with patch.dict(app.extensions, planner_db=(Mock(),sql)), patch('planner.genai.Client') as ai:
            generate = ai.return_value.__enter__.return_value.models.generate_content
            generate.side_effect = [ServerError(504, {'error':{'message':'timeout'}}), Mock(text='["wheat"]')]
            response = client.post('/planner',data=data,follow_redirects=True)
            self.assertEqual(response.status_code,200)
            self.assertIn('#planResult',response.history[0].headers['Location'])
            self.assertIn(b'id="planResult"',response.data)
            self.assertEqual([call.kwargs['model'] for call in generate.call_args_list],
                             ['gemini-3.8-flash','gemini-3.5-flash-lite'])
            generate.side_effect = ServerError(503, {'error':{'message':'busy'}})
            response = client.post('/planner',data=data)
            self.assertEqual(response.status_code,502)
            self.assertIn(b'tepung gandum</textarea>',response.data)
            self.assertIn(b'fieldErrors',response.data)

    def test_save_confirmation_and_saved_plan_target(self):
        import json
        client = app.test_client()
        plan = dict(ids=['berry_oats','beans','lentils'],slots=['Breakfast','Lunch','Dinner'],
                    goal='Maintain weight',exclude='')
        with client.session_transaction() as state:
            state.update(user_id=9, csrf_token='token', meal_draft=plan)
        sql = Mock()
        sql.return_value.lastrowid = 42
        sql.return_value.fetchall.side_effect = [
            [dict(id=42,created_at='2026-11-28',plan_json=json.dumps(plan))], []]
        db = Mock()
        with patch.dict(app.extensions, planner_db=(db,sql)):
            response = client.post('/planner',data=dict(action='save',token='token'),follow_redirects=True)
            self.assertEqual(response.status_code,200)
            self.assertIn('#saved-plan-42',response.history[0].headers['Location'])
            self.assertIn(b'id="planSavedPopup"',response.data)
            self.assertIn(b'id="saved-plan-42"',response.data)
            db.return_value.commit.assert_called_once()
            self.assertNotIn(b'id="planSavedPopup"',client.get('/planner').data)

    def test_maintain_and_muscle_goals_with_malformed_translation(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=9,csrf_token='token')
        sql = Mock()
        sql.return_value.fetchall.return_value = []
        with patch.dict(app.extensions, planner_db=(Mock(),sql)), patch('planner.genai.Client') as ai:
            generate = ai.return_value.__enter__.return_value.models.generate_content
            for goal in ('Maintain weight','Muscle gain'):
                with self.subTest(goal=goal):
                    for exclusions in ('', 'tepung gandum'):
                        generate.reset_mock()
                        generate.side_effect = [Mock(text=''),Mock(text='["wheat"]')]
                        response = client.post('/planner',data=dict(action='generate',token='token',
                            days='7',goal=goal,exclude=exclusions),follow_redirects=True)
                        self.assertEqual(response.status_code,200)
                        self.assertIn(b'id="planResult"',response.data)
                        self.assertEqual(generate.call_count,2 if exclusions else 0)
                        with client.session_transaction() as state:
                            self.assertEqual(state['meal_draft']['goal'],goal)
                            self.assertEqual(len(state['meal_draft']['ids']),21)
                            self.assertNotIn('peas',state['meal_draft']['ids'] if exclusions else [])

    def test_unclear_exclusions_point_to_field(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=9,csrf_token='token')
        sql = Mock()
        with patch.dict(app.extensions, planner_db=(Mock(),sql)), patch('planner.genai.Client') as ai:
            ai.return_value.__enter__.return_value.models.generate_content.return_value.text='[]'
            response = client.post('/planner',data=dict(action='generate',token='token',
                                   days='1',goal='Muscle gain',exclude='unclear item'))
            self.assertEqual(response.status_code,400)
            self.assertIn(b'fieldErrors',response.data)
            self.assertIn(b'unclear item</textarea>',response.data)
            sql.assert_not_called()

    def test_multilingual_bullet_preferences_and_ai_failure(self):
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=9, csrf_token='token')
        sql = Mock()
        sql.return_value.fetchall.return_value = []
        data = dict(action='generate',token='token',days='1',goal='Maintain weight',
                    preferences='Masakan Malaysia\nCepat disediakan\n少油')
        with patch.dict(app.extensions, planner_db=(Mock(),sql)), patch('planner.genai.Client') as ai:
            generate = ai.return_value.__enter__.return_value.models.generate_content
            generate.return_value.text='["beans","lentils","berry_oats"]'
            response = client.post('/planner',data=data,follow_redirects=True)
            self.assertEqual(response.status_code,200)
            self.assertIn(b'data-numbered="bullets" name="preferences"',response.data)
            self.assertIn('少油'.encode(),response.data)
            self.assertIn('in any language',generate.call_args.args[0] if generate.call_args.args else generate.call_args.kwargs['contents'])
            generate.side_effect=RuntimeError('outage')
            response=client.post('/planner',data=data)
            self.assertEqual(response.status_code,200)
            self.assertIn(b'id="planResult"',response.data)
            self.assertIn(b'extra preferences were not applied',response.data)

    def test_rate_limit_fallback_and_honest_quota_message(self):
        from google.genai.errors import ClientError
        client = app.test_client()
        with client.session_transaction() as state:
            state.update(user_id=9,csrf_token='token')
        sql = Mock()
        sql.return_value.fetchall.return_value=[]
        data=dict(action='generate',token='token',days='1',goal='Maintain weight',exclude='tepung gandum')
        with patch.dict(app.extensions,planner_db=(Mock(),sql)),patch('planner.genai.Client') as ai:
            generate=ai.return_value.__enter__.return_value.models.generate_content
            generate.side_effect=[ClientError(429,{'error':{'message':'quota'}}),Mock(text='["wheat"]')]
            response=client.post('/planner',data=data)
            self.assertEqual(response.status_code,303)
            self.assertEqual(generate.call_count,2)
            with client.session_transaction() as state:
                state.pop('meal_draft',None)
            generate.reset_mock()
            generate.side_effect=ClientError(429,{'error':{'message':'quota'}})
            response=client.post('/planner',data=data)
            self.assertEqual(response.status_code,429)
            self.assertIn(b'AI usage limit reached',response.data)
            self.assertIn(b'tepung gandum</textarea>',response.data)
            self.assertNotIn(b'id="planResult"',response.data)
            self.assertEqual(generate.call_count,2)

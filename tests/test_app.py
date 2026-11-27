import json
import os
import unittest
from unittest.mock import patch

from google.genai.errors import ServerError

os.environ['SECRET_KEY'] = 'test-only-secret'

from app import app, db, init_db, query, recipe_view  # noqa: E402


@unittest.skipUnless(
    os.environ.get('MYSQL_TEST_DATABASE', '').endswith('_test')
    and all(name in os.environ for name in ('MYSQL_TEST_HOST', 'MYSQL_TEST_USER', 'MYSQL_TEST_PASSWORD')),
    'Set MYSQL_TEST_HOST, MYSQL_TEST_USER, MYSQL_TEST_PASSWORD, and MYSQL_TEST_DATABASE ending in _test',
)
class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['MYSQL_HOST'] = os.environ['MYSQL_TEST_HOST']
        os.environ['MYSQL_PORT'] = os.environ.get('MYSQL_TEST_PORT', '4000')
        os.environ['MYSQL_USER'] = os.environ['MYSQL_TEST_USER']
        os.environ['MYSQL_PASSWORD'] = os.environ['MYSQL_TEST_PASSWORD']
        os.environ['MYSQL_DATABASE'] = os.environ['MYSQL_TEST_DATABASE']
        init_db()

    def setUp(self):
        app.config['TESTING'] = True
        with app.app_context():
            query('DELETE FROM users')
            db().commit()
        self.client = app.test_client()
        self.csrf = self._token(self.client)

    def _token(self, client):
        client.get('/')
        with client.session_transaction() as session:
            return session['csrf_token']

    def _post(self, path, data, client=None, token=None):
        return (client or self.client).post(path, json=data, headers={'X-CSRF-Token': token or self.csrf})

    def test_auth_history_favorites_and_owner_scope(self):
        self.assertEqual(self._post('/auth/register', {'email': 'a@example.com', 'password': 'long-password-a'}).status_code, 201)
        self.csrf = self._token(self.client)
        with patch('app.genai.Client') as client:
            client.return_value.__enter__.return_value = client.return_value
            client.return_value.models.generate_content.return_value.text = json.dumps(dict(title='Rice', ingredients=['rice'], steps=['Cook.']))
            made = self._post('/api/recipe', {'ingredients': 'carrots'})
            self.assertEqual(client.return_value.models.generate_content.call_args.kwargs['model'], 'gemini-3.8-flash')
            client.return_value.__exit__.assert_called_once()
        self.assertEqual(made.status_code, 200)
        recipe_id = made.json['id']
        self.assertEqual(len(self.client.get('/api/recipes').json['recipes']), 1)
        self.assertEqual(self._post(f'/api/recipes/{recipe_id}/favorite', {}).status_code, 200)
        self.assertEqual(len(self.client.get('/api/favorites').json['recipes']), 1)
        self.assertEqual(self.client.delete(f'/api/recipes/{recipe_id}/favorite').status_code, 403)

        other = app.test_client()
        token = self._token(other)
        self.assertEqual(self._post('/auth/register', {'email': 'b@example.com', 'password': 'long-password-b'}, other, token).status_code, 201)
        self.assertEqual(other.get(f'/api/recipes/{recipe_id}').status_code, 404)
        self.assertEqual(other.get('/api/recipes').json['recipes'], [])
        other_token = self._token(other)
        self.assertEqual(self._post(f'/api/recipes/{recipe_id}/favorite', {}, other, other_token).status_code, 404)

    def test_bad_input_and_login(self):
        self.assertEqual(self._post('/auth/register', {'email': 'bad', 'password': 'short'}).status_code, 400)
        self.assertEqual(self._post('/auth/login', {'email': 'missing@example.com', 'password': 'wrong'}).status_code, 401)
        with patch('app.genai.Client') as client:
            client.return_value.__enter__.return_value = client.return_value
            client.return_value.models.generate_content.return_value.text = json.dumps(dict(title='Rice', ingredients=['rice'], steps=['Cook.']))
            response = self._post('/api/recipe', {'ingredients': 'rice'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['steps'], ['Cook.'])
        self.assertEqual(self.client.get('/api/recipes').status_code, 401)
        self.assertEqual(self._post('/auth/register', {'email': 'c@example.com', 'password': 'long-password-c'}).status_code, 201)
        self.csrf = self._token(self.client)
        self.assertEqual(self._post('/api/recipe', {'ingredients': 'x' * 1001}).status_code, 400)
        self.assertEqual(self._post('/auth/logout', {}).status_code, 200)
        self.assertEqual(self.client.get('/api/recipes').status_code, 401)
        self.csrf = self._token(self.client)
        self.assertEqual(self._post('/auth/login', {'email': 'c@example.com', 'password': 'long-password-c'}).status_code, 200)

    def test_busy_model_uses_flash_lite(self):
        with patch('app.genai.Client') as client:
            client.return_value.__enter__.return_value = client.return_value
            generate = client.return_value.models.generate_content
            generate.side_effect = [ServerError(503, {'error': {'message': 'busy'}}), type('Reply', (), {'text': json.dumps(dict(title='Rice', ingredients=['rice'], steps=['Cook.']))})()]
            response = self._post('/api/recipe', {'ingredients': 'rice'})
            self.assertEqual([call.kwargs['model'] for call in generate.call_args_list],
                             ['gemini-3.8-flash', 'gemini-3.5-flash-lite'])
        self.assertEqual(response.status_code, 200)


class DeploymentTest(unittest.TestCase):
    def test_cooking_steps(self):
        self.assertEqual(recipe_view('# Soup\n## Instructions\n1. Stir.')['steps'], ['Stir.'])
        self.assertEqual(recipe_view('{"title":"Soup","ingredients":["water"],"steps":["Boil."]}')['steps'], ['Boil.'])
        with self.assertRaises(ValueError):
            recipe_view('{"title":"Soup","ingredients":["water"],"steps":[]}')

    def test_tidb_connection_uses_tls(self):
        settings = {'MYSQL_HOST': 'example.tidbcloud.com', 'MYSQL_PORT': '4000',
                    'MYSQL_USER': 'chef', 'MYSQL_PASSWORD': 'secret', 'MYSQL_DATABASE': 'ai_chef'}
        with patch.dict(os.environ, settings), patch('app.ssl.create_default_context') as tls, patch('app.pymysql.connect') as connect:
            with app.app_context():
                db()
            self.assertEqual(connect.call_args.kwargs['host'], settings['MYSQL_HOST'])
            self.assertIs(connect.call_args.kwargs['ssl'], tls.return_value)

    def test_static_assets_are_available_locally(self):
        response = app.test_client().get('/static/style.css')
        self.assertEqual(response.status_code, 200)
        response.close()


if __name__ == '__main__':
    unittest.main()

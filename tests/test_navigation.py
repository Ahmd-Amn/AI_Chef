import unittest
from html.parser import HTMLParser
from unittest.mock import Mock, patch
from app import app


class NavigationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'nav':
            self.inside = True
        if self.inside and tag == 'a':
            self.links.append((attrs.get('id'), attrs['href']))

    def handle_endtag(self, tag):
        if tag == 'nav':
            self.inside = False


class NavigationTest(unittest.TestCase):
    def test_signed_in_pages_share_navigation(self):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(user_id=1, csrf_token='token')
        query = Mock()
        query.return_value.fetchall.return_value = []
        links = []
        with patch.dict(app.extensions, planner_db=(Mock(), query)):
            for path in ('/', '/planner', '/tracker'):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-controls="primaryNavigation"', response.text)
                self.assertIn('id="primaryNavigation"', response.text)
                self.assertIn('/static/navigation.js', response.text)
                self.assertIn('>AI Chef<img class="brand-logo"', response.text)
                self.assertIn('src="/static/images/ai-chef-logo.svg" width="40" height="40" alt=""', response.text)
                self.assertIn('id="library"', response.text)
                self.assertIn('/static/library.js', response.text)
                parser = NavigationParser()
                parser.feed(response.text)
                links.append(parser.links)
                self.assertIn('data-logged-in="true">Log out', response.text)
        self.assertEqual(links[0], links[1])
        self.assertEqual(links[1], links[2])

    def test_project_name_preserves_recipe_identity(self):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(user_id=1,csrf_token='token')
        query=Mock()
        query.return_value.fetchall.return_value=[]
        with patch.dict(app.extensions,planner_db=(Mock(),query)):
            home=client.get('/').text
            self.assertIn('>AI Chef<img',home)
            self.assertIn('AI Chef — recipes',home)
            for path in ('/planner','/tracker'):
                response=client.get(path)
                self.assertEqual(response.status_code,200)
                self.assertIn('Personal AI Cooking &amp; Meal-Planning Assistant',response.text)
                self.assertIn('>AI Chef<img',response.text)

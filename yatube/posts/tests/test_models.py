from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )
        cls.str_model_test = {
            cls.group: cls.group.title,
            cls.post: cls.post.text[:15]
        }

    def test_models_have_correct_object_names(self):
        for field, expected_value in PostModelTest.str_model_test.items():
            with self.subTest(field=field):
                self.assertEqual(str(field), expected_value)

import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.user2 = User.objects.create(username='follower')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='test_description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )

        paginator_posts = 13
        for posts in range(paginator_posts):
            Post.objects.create(
                author=cls.user,
                text='Тестовый текст',
                group=cls.group,)

        cls.urls_with_paginator = (
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': 'test_slug'}),
            reverse('posts:profile', kwargs={
                'username': PostsPagesTests.user.username}),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Модуль shutil - библиотека Python с удобными инструментами
        # для управления файлами и директориями:
        # создание, удаление, копирование, перемещение,изменение папок и файлов
        # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)
        cache.clear()

    def test_pages_uses_correct_template(self):
        urls_templates = {
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html',
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': 'test_slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'auth'}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/post_create.html'
        }
        for reverse_name, template in urls_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        post = response.context['page_obj'][0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)

    def test_group_posts_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': 'test_slug'}))
        post = response.context['page_obj'][0]
        self.assertEqual(post.group, self.post.group)

    def test_profile_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': 'auth'}))
        post = response.context['page_obj'][0]
        self.assertEqual(post.author, self.post.author)

    def test_post_detail_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
        post = response.context['post'].pk
        self.assertEqual(post, self.post.pk)

    def test_post_create_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {'text': forms.fields.CharField,
                       'group': forms.fields.ChoiceField}
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                field = response.context['form'].fields[value]
                self.assertIsInstance(field, expected)

    def test_post_edit_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}))
        form_fields = {'text': forms.fields.CharField,
                       'group': forms.fields.ChoiceField}
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                field = response.context['form'].fields[value]
                self.assertIsInstance(field, expected)

    def test_index_contains_ten_records(self):
        for urls in self.urls_with_paginator:
            response = self.authorized_client.get(urls)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_context_with_image(self):
        small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                     b'\x01\x00\x80\x00\x00\x00\x00\x00'
                     b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                     b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                     b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                     b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small2.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
            group=self.group,
            image=uploaded
        )
        for url in self.urls_with_paginator:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                first_object = response.context['page_obj'][0]
                self.assertEqual(first_object.author, post.author)
                self.assertEqual(first_object.text, post.text)
                self.assertEqual(first_object.group, post.group)
                self.assertEqual(first_object.image, post.image)

    def test_caсhe(self):
        response = self.authorized_client.get('/').content
        Post.objects.create(
            author=self.user,
            text='Тестовый текст',
        )
        self.assertEqual(response, self.authorized_client.get('/').content)
        cache.clear()
        self.assertNotEqual(response, self.authorized_client.get('/').content)

    def test_follower_can_get_post(self):
        Follow.objects.create(author=self.user, user=self.user2)
        Post.objects.create(author=self.user, text='Тестовый текст')
        response = self.authorized_client2.get(reverse('posts:follow_index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object, Post.objects.first())

    def test_unfollower_cant_get_post(self):
        content1 = self.authorized_client.get(
            reverse('posts:follow_index')).content
        Post.objects.create(author=self.user2, text='Тестовый текст')
        content2 = self.authorized_client.get(
            reverse('posts:follow_index')).content
        self.assertEqual(content1, content2)

    def test_follow(self):
        follow_count = Follow.objects.count()
        Follow.objects.create(author=self.user, user=self.user2)
        self.assertEqual(follow_count + 1, Follow.objects.count())

    def test_unfollow(self):
        Follow.objects.create(author=self.user, user=self.user2)
        follow_count = Follow.objects.count()
        self.authorized_client2.get(f'/profile/{self.user.username}/unfollow/')
        self.assertEqual(follow_count - 1, Follow.objects.count())

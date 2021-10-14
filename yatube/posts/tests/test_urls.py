from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
        )

        cls.post_id_url = f'/posts/{cls.post.id}/'
        cls.group_posts_url = f'/group/{cls.group.slug}/'
        cls.post_profile_url = f'/profile/{cls.user.username}/'
        cls.post_edit_url = f'/posts/{cls.post.id}/edit/'

        cls.public_urls = {
            '/': "posts/index.html",
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
            cls.post_id_url: 'posts/post_detail.html',
            cls.group_posts_url: 'posts/group_list.html',
            cls.post_profile_url: 'posts/profile.html',
        }
        cls.post_create_url = {'/create/': 'posts/post_create.html'}
        cls.post_edit_template = {cls.post_edit_url: 'posts/post_create.html'}
        cls.follow_index_url = {'/follow/': 'posts/follow.html'}
        cls.following_urls = {
            f'/profile/{cls.user.username}/follow/': 'posts/profile.html',
            f'/profile/{cls.user.username}/unfollow/': 'posts/profile.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_urls_public_pages(self):
        """Проверяем доступность страниц неавторизованному пользователю"""
        for address in URLTests.public_urls:
            with self.subTest(field=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, 200)

    def test_url_user_page(self):
        """Проверяем доступность страницы create"""
        """для авторизованного пользователя"""
        for address in URLTests.post_create_url:
            with self.subTest(field=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, 200)

    def test_guest_redirect_post_create(self):
        """Проверяем редирект неавторизованного пользователя на"""
        """странице create"""
        for address in URLTests.post_create_url:
            with self.subTest(field=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, ('/auth/login/?next=/create/'))

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for address, template in URLTests.public_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_author_post_edit(self):
        """Проверяем доступность страницы post_edit автору."""
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_unexisting_page(self):
        """Проверяем запрос к несуществующей странице вернёт ошибку 404."""
        response = self.guest_client.get('2224rwfw2/')
        self.assertEqual(response.status_code, 404)

    def test_404_use_custom_template(self):
        response = self.guest_client.get('/nonexist-page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_follow_index_url_user_page(self):
        """Проверяем верность щаблона и доступность страницы follow."""
        """для авторизованного пользователя"""
        for address, template in URLTests.follow_index_url.items():
            with self.subTest(field=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    def test_follow_urls_user_page(self):
        """Проверяем редирект авторизованного пользователя на"""
        """странице follow"""
        for address in URLTests.following_urls:
            with self.subTest(field=address):
                response = self.authorized_client.get(address, follow=True)
                self.assertRedirects(response, self.post_profile_url)

from django.core.management.base import BaseCommand
from accounts.models import User
from django.core.management import CommandError



class Command(BaseCommand):
    help = 'Create a superuser or admin user with specified user_type'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Username for the user')
        parser.add_argument('--email', required=True, help='Email for the user')
        parser.add_argument('--password', required=True, help='Password for the user')
        parser.add_argument('--user-type', choices=['admin', 'superadmin'], required=True,
                          help='Type of user to create')
        parser.add_argument('--first-name', help='First name of the user')
        parser.add_argument('--last-name', help='Last name of the user')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        user_type = options['user_type']
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')

        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')

        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists.')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type,
            is_staff=True if user_type in ['admin', 'superadmin'] else False,
            is_superuser=True if user_type == 'superadmin' else False
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {user_type} "{username}"')
        )

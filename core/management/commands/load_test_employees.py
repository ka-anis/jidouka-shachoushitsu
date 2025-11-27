"""
Management command to load test employees for development and testing.
Use this to populate a fresh database with a small set of test employees.

Usage:
    python manage.py load_test_employees
"""

from django.core.management.base import BaseCommand
from core.models import Employee, Role


class Command(BaseCommand):
    help = 'Load test employees into the database for development and testing'

    def handle(self, *args, **options):
        # Clear existing employees
        Employee.objects.all().delete()
        self.stdout.write("Cleared existing employees")
        
        # Test employee data
        test_employees = [
            {
                'name': 'メンバー１',
                'email': 'khaled.gad@ejust.edu.eg',
                'employee_id': 'TEST001',
                'order': 1,
                'order_gyomu': 1,
                'role': Role.MEMBER,
                'is_rotation_active': True,
            },
            {
                'name': 'メンバー２',
                'email': 'gad.khaled00@gmail.com',
                'employee_id': 'TEST002',
                'order': 2,
                'order_gyomu': 2,
                'role': Role.MEMBER,
                'is_rotation_active': True,
            },
            {
                'name': 'メンバー３',
                'email': 'k-mahrous@ar-system.co.jp',
                'employee_id': 'TEST003',
                'order': 3,
                'order_gyomu': 3,
                'role': Role.MEMBER,
                'is_rotation_active': True,
            },
            {
                'name': 'テスト４',
                'email': 'test.employee4@example.com',
                'employee_id': 'TEST004',
                'order': 4,
                'order_gyomu': 4,
                'role': Role.MEMBER,
                'is_rotation_active': True,
            },
            {
                'name': 'テスト５',
                'email': 'test.employee5@example.com',
                'employee_id': 'TEST005',
                'order': 5,
                'order_gyomu': 5,
                'role': Role.MEMBER,
                'is_rotation_active': True,
            },
        ]
        
        created_count = 0
        for emp_data in test_employees:
            employee, created = Employee.objects.get_or_create(
                email=emp_data['email'],
                defaults={
                    'name': emp_data['name'],
                    'employee_id': emp_data['employee_id'],
                    'order': emp_data['order'],
                    'order_gyomu': emp_data['order_gyomu'],
                    'role': emp_data['role'],
                    'is_rotation_active': emp_data['is_rotation_active'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created: {emp_data["name"]} ({emp_data["email"]})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'✓ Already exists: {emp_data["name"]} ({emp_data["email"]})'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Test employees loaded successfully ({created_count} new employees created)'
            )
        )

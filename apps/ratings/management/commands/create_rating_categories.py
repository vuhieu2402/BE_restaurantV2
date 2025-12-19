from django.core.management.base import BaseCommand
from apps.ratings.models import RatingCategory


class Command(BaseCommand):
    help = 'Create default rating categories for detailed rating aspects'

    def handle(self, *args, **options):
        """Create default rating categories"""
        default_categories = [
            {
                'name': 'Taste',
                'code': 'taste',
                'description': 'Overall taste and flavor of the dish',
                'display_order': 1
            },
            {
                'name': 'Presentation',
                'code': 'presentation',
                'description': 'Visual appearance and plating',
                'display_order': 2
            },
            {
                'name': 'Value for Money',
                'code': 'value',
                'description': 'Price-quality ratio and overall value',
                'display_order': 3
            },
            {
                'name': 'Portion Size',
                'code': 'portion_size',
                'description': 'Amount of food served and satisfaction level',
                'display_order': 4
            },
            {
                'name': 'Service Quality',
                'code': 'service',
                'description': 'Staff service and dining experience',
                'display_order': 5
            }
        ]

        created_count = 0
        updated_count = 0

        for category_data in default_categories:
            category, created = RatingCategory.objects.get_or_create(
                code=category_data['code'],
                defaults=category_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created rating category: {category.name}')
                )
            else:
                # Update existing category with latest data
                for field, value in category_data.items():
                    if field != 'code':  # Don't update the code
                        setattr(category, field, value)
                category.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated rating category: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nRating categories setup complete!\n'
                f'Created: {created_count}\n'
                f'Updated: {updated_count}\n'
                f'Total categories: {RatingCategory.objects.count()}'
            )
        )
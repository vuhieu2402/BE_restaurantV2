"""
Management command để cleanup expired refresh token sessions và verification codes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from apps.authentications.models import RefreshTokenSession, VerificationCode
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired refresh token sessions and verification codes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about cleanup process',
        )
        parser.add_argument(
            '--sessions-only',
            action='store_true',
            help='Only cleanup refresh token sessions',
        )
        parser.add_argument(
            '--codes-only',
            action='store_true',
            help='Only cleanup verification codes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        sessions_only = options['sessions_only']
        codes_only = options['codes_only']

        self.stdout.write(
            self.style.SUCCESS('Starting cleanup process...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No actual deletion will occur')
            )

        try:
            total_cleaned = 0

            # Cleanup expired refresh token sessions
            if not codes_only:
                sessions_cleaned = self.cleanup_sessions(dry_run, verbose)
                total_cleaned += sessions_cleaned
                self.stdout.write(f'Sessions cleaned: {sessions_cleaned}')

            # Cleanup expired verification codes
            if not sessions_only:
                codes_cleaned = self.cleanup_codes(dry_run, verbose)
                total_cleaned += codes_cleaned
                self.stdout.write(f'Verification codes cleaned: {codes_cleaned}')

            if verbose:
                self.stdout.write(f'Total items cleaned: {total_cleaned}')

            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully cleaned up {total_cleaned} expired items'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would clean up {total_cleaned} expired items'
                    )
                )

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'Error during cleanup: {str(e)}')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('Cleanup process completed successfully')
        )

    def cleanup_sessions(self, dry_run, verbose):
        """Cleanup expired refresh token sessions"""
        try:
            expired_sessions = RefreshTokenSession.objects.filter(
                expires_at__lt=timezone.now(),
                is_active=True
            )

            if dry_run:
                count = expired_sessions.count()
                if verbose:
                    for session in expired_sessions:
                        self.stdout.write(f"  Would expire session: {session}")
                return count

            # Mark as expired (soft delete)
            count = expired_sessions.update(
                is_active=False,
                revoked_at=timezone.now(),
                revoked_reason='expired'
            )

            return count

        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")
            return 0

    def cleanup_codes(self, dry_run, verbose):
        """Cleanup expired verification codes"""
        try:
            expired_codes = VerificationCode.objects.filter(
                models.Q(expires_at__lt=timezone.now()) |
                models.Q(is_used=True) |
                models.Q(attempts__gte=models.F('max_attempts'))
            )

            if dry_run:
                count = expired_codes.count()
                if verbose:
                    for code in expired_codes[:10]:  # Limit output
                        self.stdout.write(f"  Would delete code: {code}")
                    if expired_codes.count() > 10:
                        self.stdout.write(f"  ... and {expired_codes.count() - 10} more")
                return count

            count = expired_codes.count()
            expired_codes.delete()  # Hard delete verification codes

            return count

        except Exception as e:
            logger.error(f"Verification code cleanup error: {str(e)}")
            return 0

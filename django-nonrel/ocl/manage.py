#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oclapi.settings.local')
    os.environ.setdefault('DJANGO_CONFIGURATION', 'Local')

    from configurations.management import execute_from_command_line

    if os.getenv("NEW_RELIC_API_KEY") and os.getenv("DJANGO_CONFIGURATION") in ['Production', 'Showcase', 'Staging']:
        import newrelic.agent
        newrelic.agent.initialize('newrelic-api.ini')

    execute_from_command_line(sys.argv)

import pickle
from pathlib import Path
from googleapiclient.discovery import build, Resource
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from typing import List


class GoogleService:
    """Represents a connection to Google Directory. Attributes are various scopes/permissions of connections.

    Attributes:
        directory_service (Resource): A Resource object with methods for interacting with the GSuite Directory. Has
            DIRECTORY_SCOPES as its permissions.

    Todo:
        Implement additional scopes for logging
    """

    # If modifying these scopes, delete the file token.pickle.
    # TODO: Move scopes to environment variable
    # TODO: Redo auth to be service account based and generate credentials using superuser at first run
    DIRECTORY_SCOPES: List[str]= ['https://www.googleapis.com/auth/admin.directory.user',
              'https://www.googleapis.com/auth/admin.directory.group',
              'https://www.googleapis.com/auth/admin.directory.group.member',
              'https://www.googleapis.com/auth/admin.directory.device.chromeos']  #: Access given to self.directory_service
    GROUP_SETTINGS_SCOPES: List[str] = ['https://www.googleapis.com/auth/apps.groups.settings'] #Access given to self.group_settings_service
    DRIVE_SCOPES: List[str] = ['https://www.googleapis.com/auth/drive.file',
                               'https://www.googleapis.com/auth/drive']  #: Access given to self.drive_service
    REPORTS_SCOPES: List[str] = ['https://www.googleapis.com/auth/admin.reports.audit.readonly',
                                 'https://www.googleapis.com/auth/admin.reports.usage.readonly']
    CLASSROOM_SCOPES: List[str] =['https://www.googleapis.com/auth/classroom.courses.readonly',
                                  'https://www.googleapis.com/auth/classroom.rosters.readonly',
                                  'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
                                  'https://www.googleapis.com/auth/classroom.student-submissions.students.readonly']
    LICENSING_SCOPES: List[str] = ['https://www.googleapis.com/auth/apps.licensing']
    SPREADSHEETS_SCOPES: List[str] = ['https://www.googleapis.com/auth/spreadsheets']
    # TODO: Refactor creds to environment variables.
    creds_dir = Path(Path(__file__).parents[2], 'creds')

    def __init__(self):
        print("Establishing connection to GSuite.")
        self.directory_service = self.get_directory_service()
        self.drive_service = self.get_drive_service()
        self.group_settings_service = self.get_group_settings_service()
        self.licensing_service = self.get_licensing_service()
        self.spreadsheet_service = self.get_spreadsheets_service()

    # TODO: refactor services into get_service

    @staticmethod
    def get_service(api_name: str, api_version: str, api_scopes: List[str]) -> Resource:
        """
        Helper method that will generate an API Resource Object for an arbitrary Google API.
        Args:
            api_name: String of which API we should communicate with
            api_version: String of the API version, which may be in the format v1, or in the format directory_v1.
                     The format depends on the API and if that API has different versioning per category.
            api_scopes: A list of strings containing the Scopes of access we are granting this Resource Object.

        Returns:
            Google API Resource Object that allows API calls to be made against the specified API.

        Creates:
            An access token authorizing the request is saved to the filesystem if not already present.
            # TODO: Lockdown token filesystem permissions to the script user automatically.
        """
        creds = None
        token_filepath = Path(GoogleService.creds_dir, f'{api_name}_{api_version}_token.pickle')
        creds_filepath = Path(GoogleService.creds_dir, 'credentials.json')
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if Path.exists(token_filepath):
            with open(token_filepath, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_filepath, api_scopes)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_filepath, 'wb') as token:
                pickle.dump(creds, token)

        service = build(api_name, api_version, credentials=creds)
        return service


    @staticmethod
    def get_directory_service() -> Resource:
        """
        Helper method that creates a connection to Google Directory. Should not be invoked directly. Instead use
        self.directory_service to avoid rebuilding the connection over and over.

        Returns:
            A Resource object with methods for interacting with the Google Workspace Directory.
        """
        service = GoogleService.get_service(api_name='admin',
                                            api_version='directory_v1',
                                            api_scopes=GoogleService.DIRECTORY_SCOPES)

        return service

    @staticmethod
    def get_group_settings_service() -> Resource:
        """
        Helper method that creates a connection to Google Group Settings. Should not be invoked directly. Instead use
        self.group_settings_service to avoid rebuilding the connection over and over.

        Returns:
            A Resource object with methods for interacting with the Google Group Settings.
        """
        service = GoogleService.get_service(api_name='groupssettings',
                                            api_version='v1',
                                            api_scopes=GoogleService.GROUP_SETTINGS_SCOPES)

        return service

    @staticmethod
    def get_drive_service() -> Resource:
        """
        Helper method that creates a connection to Google Drive. Should not be invoked directly. Instead use
        self.drive_service to avoid rebuilding the connection over and over.

        Returns:
            A Resource object with methods for interacting with the Google Drive.
        """
        service = GoogleService.get_service(api_name='drive',
                                            api_version='v3',
                                            api_scopes=GoogleService.DRIVE_SCOPES)

        return service

    @staticmethod
    def get_reports_service() -> Resource:
        """
        Helper method that creates a connection to Google Admin Reports. Should not be invoked directly. Instead use
        self.report_service to avoid rebuilding the connection over and over.

        Returns:
            A Resource object with methods for interacting with the GSuite Admin Reports.
        """
        service = GoogleService.get_service(api_name='admin',
                                            api_version='reports_v1',
                                            api_scopes=GoogleService.REPORTS_SCOPES)

        return service

    @staticmethod
    def get_classroom_service() -> Resource:
        """
        Helper method that creates a connection to Google Classroom. Should not be invoked directly. Instead use
        self.classroom_service to avoid rebuilding the connection over and over.

        Returns:
            A Resource object with methods for interacting with the Google Classroom.
        """
        service = GoogleService.get_service(api_name='classroom',
                                            api_version='v1',
                                            api_scopes=GoogleService.CLASSROOM_SCOPES)

        return service

    @staticmethod
    def get_licensing_service() -> Resource:
        """
        Helper method that creates a connection to Google Workspace Licensing. Should not be invoked directly. Instead use
        self.licensing_service to avoid rebuilding the connection over and over.

        Returns:
            A Resource object with methods for interacting with the GSuite Directory.
        """
        service = GoogleService.get_service(api_name='licensing',
                                            api_version='v1',
                                            api_scopes=GoogleService.LICENSING_SCOPES)

        return service

    @staticmethod
    def get_spreadsheets_service() -> Resource:
        """
        Helper method that creates a connection to Google Sheets. Should not be invoked directly. Instead use
        self.sheets_service to avoid rebuilding the connection over and over.

        Returns:
            A Resource object with methods for interacting with the Google Sheets.
        """
        service = GoogleService.get_service(api_name='sheets',
                                            api_version='v4',
                                            api_scopes=GoogleService.SPREADSHEETS_SCOPES)

        return service

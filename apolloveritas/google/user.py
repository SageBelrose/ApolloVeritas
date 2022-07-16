from __future__ import annotations
from typing import Dict, List

from googleapiclient.errors import HttpError
from apolloveritas.google.group import GoogleGroup
from apolloveritas.google.service import GoogleService
from apolloveritas.utils.utils import str_missing_key
from pathlib import Path
import json


class GoogleUser:
    service_instance = GoogleService()
    service = service_instance.directory_service
    licensing_service = service_instance.licensing_service
    # TODO: Refactor conf contents to not manually editing a textfile
    defaults_filepath = Path(Path(__file__).parents[2], 'conf', 'google_user_defaults.json')
    with open(defaults_filepath, 'r') as defaults_file:
        defaults = json.load(defaults_file)

    def __init__(self, service, user_dict: Dict, lazy_load: bool = True):
        self.immutable_dict = user_dict
        self.service: GoogleService().directory_service = service
        self.dict = user_dict
        self.fill_from_dict()
        if not lazy_load:
            self.groups = self.get_all_groups()
        self.json = self.jsonify()

    def fill_from_dict(self):
        # TODO: Make this code more elegant
        while True:
            try:
                self.addresses = self.dict['addresses']
                self.posixAccounts = self.dict['posixAccounts']
                self.phones = self.dict['phones']
                self.locations = self.dict['locations']
                self.isDelegatedAdmin = self.dict['isDelegatedAdmin']
                self.recoveryPhone = self.dict['recoveryPhone']
                self.suspended = self.dict['suspended']
                self.keywords = self.dict['keywords']
                self.id = self.dict['id']
                self.aliases = self.dict['aliases']
                self.nonEditableAliases = self.dict['nonEditableAliases']
                self.archived = self.dict['archived']
                self.deletionTime = self.dict['deletionTime']
                self.suspensionReason = self.dict['suspensionReason']
                self.thumbnailPhotoUrl = self.dict['thumbnailPhotoUrl']
                self.isEnrolledIn2Sv = self.dict['isEnrolledIn2Sv']
                self.isAdmin = self.dict['isAdmin']
                self.relations = self.dict['relations']
                self.includeInGlobalAddressList = self.dict['includeInGlobalAddressList']
                self.languages = self.dict['languages']
                self.ims = self.dict['ims']
                self.etag = self.dict['etag']
                self.lastLoginTime = self.dict['lastLoginTime']
                self.orgUnitPath = self.dict['orgUnitPath']
                self.agreedToTerms = self.dict['agreedToTerms']
                self.externalIds = self.dict['externalIds']
                self.ipWhitelisted = self.dict['ipWhitelisted']
                self.sshPublicKeys = self.dict['sshPublicKeys']
                self.customSchemas = self.dict['customSchemas']
                self.isEnforcedIn2Sv = self.dict['isEnforcedIn2Sv']
                self.isMailboxSetup = self.dict['isMailboxSetup']
                self.primaryEmail = self.dict['primaryEmail']
                self.password = self.dict['password']
                self.emails = self.dict['emails']
                self.organizations = self.dict['organizations']
                self.kind = self.dict['kind']
                self.hashFunction = self.dict['hashFunction']
                self.name = self.dict['name']
                self.givenName = self.name['givenName']
                self.familyName = self.name['familyName']
                self.fullName = self.name.get('fullName')
                self.gender = self.dict['gender']
                self.notes = self.dict['notes']
                self.creationTime = self.dict['creationTime']
                # TODO: Refactor this.
                try:
                    self.ad_account = \
                    self.dict.get('customSchemas').get('Enhanced_desktop_security').get('AD_accounts')[0].get('value')
                except AttributeError:
                    self.ad_account = None
                self.websites = self.dict['websites']
                self.changePasswordAtNextLogin = self.dict['changePasswordAtNextLogin']
                self.recoveryEmail = self.dict['recoveryEmail']
                self.customerId = self.dict['customerId']
                self.thumbnailPhotoEtag = self.dict['thumbnailPhotoEtag']
                break
            except KeyError as missing_key:
                self.dict[str_missing_key(missing_key)] = None
                continue

    def patch(self):
        """
            Takes the current state of the GoogleUser in memory and tells Google to update all properties.
        Returns:
            API Call response
        """
        result = self.service.users().patch(userKey=self.id, body=self.jsonify()).execute()
        return result

    def jsonify(self) -> Dict:
        """
            Takes the class instance of GoogleUser and turns it into the JSON format expected by the API.
        Returns:
            Dictionary object representing what the Directory API expects in a JSON object.
        """
        return {
            # JSON template for User object in Directory API.
            "addresses": self.addresses,
            "posixAccounts": self.posixAccounts,
            "phones": self.phones,
            "locations": self.locations,
            "isDelegatedAdmin": self.isDelegatedAdmin,  # Boolean indicating if the user is delegated admin (Read-only)
            "recoveryPhone": self.recoveryPhone,
            # Recovery phone of the user. The phone number must be in the E.164 format, starting with the plus sign (+). Example: +16506661212.
            "suspended": self.suspended,  # Indicates if user is suspended.
            "keywords": self.keywords,
            "id": self.id,  # Unique identifier of User (Read-only)
            "aliases": self.aliases,
            "nonEditableAliases": self.nonEditableAliases,
            "archived": self.archived,  # Indicates if user is archived.
            "deletionTime": self.deletionTime,
            "suspensionReason": self.suspensionReason,  # Suspension reason if user is suspended (Read-only)
            "thumbnailPhotoUrl": self.thumbnailPhotoUrl,  # Photo Url of the user (Read-only)
            "isEnrolledIn2Sv": self.isEnrolledIn2Sv,  # Is enrolled in 2-step verification (Read-only)
            "isAdmin": self.isAdmin,  # Boolean indicating if the user is admin (Read-only)
            "relations": self.relations,
            "includeInGlobalAddressList": self.includeInGlobalAddressList,
            # Boolean indicating if user is included in Global Address List
            "languages": self.languages,
            "ims": self.ims,
            "etag": self.etag,  # ETag of the resource.
            "lastLoginTime": self.lastLoginTime,  # User's last login time. (Read-only)
            "orgUnitPath": self.orgUnitPath,  # OrgUnit of User
            "agreedToTerms": self.agreedToTerms,  # Indicates if user has agreed to terms (Read-only)
            "externalIds": self.externalIds,
            "ipWhitelisted": self.ipWhitelisted,  # Boolean indicating if ip is whitelisted
            "sshPublicKeys": self.sshPublicKeys,
            "customSchemas": self.customSchemas,
            "isEnforcedIn2Sv": self.isEnrolledIn2Sv,  # Is 2-step verification enforced (Read-only)
            "isMailboxSetup": self.isMailboxSetup,  # Is mailbox setup (Read-only)
            "primaryEmail": self.primaryEmail,  # username of User
            "password": self.password,  # User's password
            "emails": self.emails,
            "organizations": self.organizations,
            "kind": self.kind,  # Kind of resource this is.
            "hashFunction": self.hashFunction,  # Hash function name for password. Supported are MD5, SHA-1 and crypt
            "name": {  # JSON template for name of a user in Directory API. # User's name
                "givenName": self.givenName,  # First Name
                "fullName": self.fullName,  # Full Name
                "familyName": self.familyName,  # Last Name
            },
            "gender": self.gender,
            "notes": self.notes,
            "creationTime": self.creationTime,  # User's G Suite account creation time. (Read-only)
            "customSchemas": {
                'Enhanced_desktop_security': {'AD_accounts': [{'type': 'work', 'value': self.ad_account}]}},
            "websites": self.websites,
            "changePasswordAtNextLogin": self.changePasswordAtNextLogin,
            # Boolean indicating if the user should change password in next login
            "recoveryEmail": self.recoveryEmail,  # Recovery email of the user.
            "customerId": self.customerId,  # CustomerId of User (Read-only)
            "thumbnailPhotoEtag": self.thumbnailPhotoEtag,  # ETag of the user's photo (Read-only)
        }

    def assign_license(self, license_type: str):
        """
        Assigns a Google Workspace EDU license. Must specify "Teacher" or "Student" license.
        Args:
            license_type:

        Returns:

        """
        # TODO: Move product IDs to configuration file
        # TODO: Auto-lookup via a dictionary or group membership
        # TODO: Improve code logic to be more flexible
        license_productId = '101031'
        teacher_license_skuId = '1010310002'
        body = {'userId': self.primaryEmail}
        if license_type == "Teacher":
            self.licensing_service.licenseAssignments().insert(productId='101031', skuId='1010310002', body=body).execute()
        elif license_type == "Student":
            pass
        else:
            raise ValueError('Invalid license type. Specify either Teacher or Student')

    def get_all_groups(self) -> List[GoogleGroup]:
        """
        Queries Google Groups API for a list of all the user's groups.
        Then loads all the groups.
        Returns:
            List of GoogleGroups object where GoogleUser in GoogleGroup.members == True
        """
        groups = []
        result = self.service.groups().list(userKey=self.primaryEmail).execute()
        if result.get('groups'):
            for group in result.get('groups'):
                groups.append(GoogleGroup(service=self.service,
                                          settings_service=GoogleService.get_group_settings_service(),
                                          group=group))
        return groups


    @staticmethod
    def get_licensed_users(license_type: str) -> List[str]:
        """
        Get a list of users who have assigned Google Workspace Licenses
        Args:
            license_type: string of either Teacher or Student

        Returns:
            List of GoogleUser.primaryEmail
        """
        # TODO: Remove hardcoded values
        license_productId = '101031'
        teacher_license_skuId = '1010310002'
        page_token = "Dummy"
        licenses = []
        if license_type == "Teacher":
            while page_token:
                result = GoogleUser.licensing_service.licenseAssignments().listForProductAndSku(productId=license_productId,
                                                                                          skuId=teacher_license_skuId,
                                                                                          customerId='springfield-schools.org',
                                                                                          pageToken=page_token,
                                                                                          maxResults=1000).execute()
                for item in result.get('items'):
                    licenses.append(item)
                page_token = result.get('nextPageToken')
        elif license_type == "Student":
            pass
        else:
            raise ValueError('Invalid license type. Specify either Teacher or Student')
        users = []
        for license in licenses:
            users.append(license.get('userId'))
        return users

    @staticmethod
    def get_user_by_email(service: GoogleService().directory_service, email: str, lazy_load: bool=True) -> GoogleUser:
        """
        Gets a single GoogleUser by their email
        Args:
            service: GoogleService.directory_service object used to make the query.
            email: the email of the user we want
            lazy_load: Do we want to load things like their groups?

        Returns:
            A single GoogleUser object
        """
        # TODO: Error handling
        result: Dict = service.users().get(userKey=email, projection='full').execute()
        user: GoogleUser = GoogleUser(service, result, lazy_load=lazy_load)
        return user

    @staticmethod
    def new_user_body(primaryEmail: str, givenName: str, familyName: str, password: str, optionalValues: Dict = None):
        """
            Creates the JSON Body for a new user account in Google Workspace.
        Args:
            primaryEmail: User's email address
            givenName: first name
            familyName: last name
            password: plaintext password yes this is bad # TODO: don't do plaintext passwords
            optionalValues: inject any key,value pairs as a dictionary. Valid attrs are found in API Docs

        Returns:
            Body for a new Google User API Call
        """
        # todo: handle error 409 if user already exists
        body = {
            "name": {
                "familyName": familyName,
                "givenName": givenName
            },
            "password": password,
            "primaryEmail": primaryEmail
        }
        if optionalValues:
            for k, v in optionalValues.items():
                if v is not None and k not in body.keys():
                    body[k] = v
                if k == 'fullName':
                    body['name'] = {
                        "familyName": familyName,
                        "givenName": givenName,
                        "fullName": v
                    }
        config_filepath = Path(Path(__file__).parents[2], 'config', 'google_user_defaults.json')
        with open(config_filepath, 'r') as config_file:
            config = json.load(config_file)
        for k, v in config.items():
            if v is not None and k not in body.keys():
                body[k] = v
        return body

    @staticmethod
    def create_in_gsuite(service: GoogleService().directory_service, body: Dict) -> GoogleUser:
        """
        Take a mocked user and create them in Google Workspace.
        Args:
            service: Google API Resource for Admin_Directory_v1
            body: Dictionary representation of the API Request JSON Body. Use new_user_body to generate this.

        Returns:
            GoogleUser object representing the created user.
        """
        try:
            result = service.users().insert(body=body).execute()
        except HttpError as e:
            print(e)
            print(body)
            raise e
        return GoogleUser(service, result)

    @staticmethod
    def get_all_users(service: GoogleService().directory_service, query: str = 'orgUnitPath=/') -> List[GoogleUser]:
        """
        Query Google Workspace and return all GoogleUsers within a given OU, recurses through sub-OUs.
        Args:
            service: GoogleService().directory_service
            query: Can be a custom query for users().list(), or use orgUnitPath=/ to get everyone.

        Returns:
            A list of all GoogleUsers that match the query.
        """
        print("Loading all GSuite Users. This may take awhile.")
        out_list = []
        nextPageToken = 'dummy'
        while nextPageToken != '':
            if nextPageToken == 'dummy':
                results = service.users().list(customer='my_customer',
                                               projection='full',
                                               maxResults=500,
                                               query=query).execute()
            else:
                results = service.users().list(customer='my_customer',
                                               projection='full',
                                               maxResults=500,
                                               query=query,
                                               pageToken=nextPageToken).execute()
            try:
                nextPageToken = results['nextPageToken']
            except KeyError:
                nextPageToken = ''
            try:
                results = results['users']
            except KeyError:
                return []
            if results:
                for user in results:
                    out_list.append(GoogleUser(service=service, user_dict=user))
        if len(out_list) > 0:
            return out_list
        else:
            return []

    @staticmethod
    def get_user_email_from_id(id: str):
        # TODO: Figure out what this method does.
        try:
            result = GoogleUser.service.users().get(userKey=id).execute()
            return result['primaryEmail']
        except HttpError:
            return f'Could not find a user with the id: {id}'

    # todo: methods - Reset password? add to group, remove from group, enable/disable/ alter fields
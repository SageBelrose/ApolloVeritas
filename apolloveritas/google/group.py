from __future__ import annotations
from typing import Dict, List, Union


class GoogleGroup():
    """Represents a group within GSuite. Use GoogleGroup().get_from_gsuite() to grab an existing group.
    Use GoogleGroup().create_in_gsuite() to create a new group to get a properly formatted GoogleGroup object.
    You shouldn't ever be manually constructing this class.

    Args:
        service (GoogleService.directory_service): The connection that is being used to access Gsuite.
        group (Dict): A dictionary containing all the data of the group.

    """
    # TODO: Move permissions to configuration file
    # TODO: better return values on class methods
    internal_distribution_list_settings = {
        'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
        'whoCanViewGroup': 'ALL_MEMBERS_CAN_VIEW',  # this is who can view messages, not the group itself
        'whoCanPostMessage': 'ALL_IN_DOMAIN_CAN_POST',
        'showInGroupDirectory': True,
        'whoCanContactOwner': 'ALL_IN_DOMAIN_CAN_CONTACT',
        'whoCanDiscoverGroup': 'ALL_IN_DOMAIN_CAN_DISCOVER',
        'isArchived': False,
        'archiveOnly': False
    }
    public_distribution_list_settings = {
        'whoCanViewMembership': 'ALL_IN_DOMAIN_CAN_VIEW',
        'whoCanViewGroup': 'ALL_MEMBERS_CAN_VIEW',  # this is who can view messages, not the group itself
        'whoCanPostMessage': 'ANYONE_CAN_POST',
        'showInGroupDirectory': True,
        'whoCanContactOwner': 'ALL_IN_DOMAIN_CAN_CONTACT',
        'whoCanDiscoverGroup': 'ALL_IN_DOMAIN_CAN_DISCOVER',
        'isArchived': False,
        'archiveOnly': False
    }
    security_group_settings = {
        'whoCanJoin': 'INVITED_CAN_JOIN',
        'whoCanViewMembership': 'ALL_OWNERS_CAN_VIEW',
        'whoCanViewGroup': 'ALL_OWNERS_CAN_VIEW',
        'isArchived': False,
        'archiveOnly': False,
        'showInGroupDirectory': False,
        'includeInGlobalAddressList': False,
        'whoCanPostMessage': 'ALL_OWNERS_CAN_POST'
    }

    def __init__(self, service, settings_service, group: Dict):
        self.kind: str = group['kind']  #: This should always be admin#directory#group.
        self.id: str = group['id']  #: UUID for the group create by google. Use this when possible for lookups.
        self.etag = group['etag']  #:
        self.email: str = group['email']  #: Email Address for this group. Important for syncing with LDAP.
        self.name: str = group['name']  #: Name of the group.
        self.directMembersCount: int = group[
            'directMembersCount']  #: How many users are in the group. Doesn't count nested.
        self.description: str = group['description']  #: Details about what the group's purpose is.
        self.adminCreated: bool = group['adminCreated']  #: True if made by admin. False if user-created.
        self.nonEditableAliases: Union[List[str], None] = group.get(
            ['nonEditableAliases'])  #: Other emails that will reach the group.
        # end google used properties
        # begin internal used properties
        self.service = service
        self.settings_service = settings_service
        self.members: List[str] = self.get_members()  #: Email Addresses of direct members of the group.
        self.json: Dict = self.jsonify()  #: Google API friendly representation of the data.
        self.settings = settings_service.groups().get(groupUniqueId=self.email).execute()

    def get_members(self) -> List[str]:
        """
        Used to obtain a list of all members in the group.

        Returns:
            A list of all members in the group.
        """
        out_list = []
        nextPageToken = 'dummy'
        while nextPageToken != '':
            if nextPageToken == 'dummy':
                results = self.service.members().list(groupKey=self.id).execute()
            else:
                results = self.service.members().list(groupKey=self.id, pageToken=nextPageToken).execute()
            try:
                nextPageToken = results['nextPageToken']
            except KeyError:
                nextPageToken = ''
            try:
                results = results['members']
            except KeyError:
                return []
            for user in results:
                out_list.append(user['email'])
        return out_list

    def add_member(self, email: str) -> None:
        """
        Used to add a single member to the group.

        Args:
            email: Email of the user you want to add to this group.

        Returns:
            None
        """
        # TODO: Parameterize role
        body = {
            "email": email,
            "role": "MEMBER",
        }
        self.service.members().insert(groupKey=self.id, body=body).execute()
        self.members = self.get_members()

    def delete_member(self, email: str) -> None:
        """
        Used to add a single member to the group.

        Args:
            email: Email of the user you want to remove from this group.

        Returns:
            None
        """
        self.service.members().delete(groupKey=self.id, memberKey=email).execute()
        self.members = self.get_members()

    def has_member(self, email: str) -> bool:
        """
        Used to check if a single member is within the group. Makes an API call, so should only be used for checking
        a single user or performance will suffer. If checking bulk users then use something like if user in self.members

        Args:
            email: User you want to know if is in the group.

        Returns:
            Whether or not the user is in this group.
        """
        r = self.service.members().hasMember(groupKey=self.id, memberKey=email).execute()
        return r['isMember']

    def set_owner(self, owner: str) -> bool:
        """
        Used to change the role of a member to owner.

        Args:
            owner: email or uuid of the user you want to change this groups owner to.

        Returns:
            bool: True if successful else False.
        """
        # TODO: Improve error handling
        try:
            member_json = self.service.members().get(groupKey=self.id, memberKey=owner).execute()
            member_json['role'] = 'OWNER'
            result = self.service.members().update(groupKey=self.id, memberKey=owner, body=member_json).execute()
            return True
        except Exception as e:
            raise e
            return False

    def jsonify(self) -> Dict:
        """
        Helper function to get an object that is more friendly to upload to Google. Use this method before making a
        direct update request to Google.

        Returns:
            Properly formatting Dict object that conforms to Directory API v1 specifications.
        """
        return {  # JSON template for Group resource in Directory API.
            "nonEditableAliases": [self.nonEditableAliases],  # List of non editable aliases (Read-only)
            "kind": "admin#directory#ldap",  # Kind of resource this is.
            "description": self.description,  # Description of the ldap
            "name": self.name,  # Group name
            "adminCreated": self.adminCreated,  # Is the ldap created by admin (Read-only) *
            "directMembersCount": self.directMembersCount,  # Group direct members count
            "id": self.id,  # Unique identifier of Group (Read-only)
            "etag": self.etag,  # ETag of the resource.
            "email": self.email,  # Email of Group
            "aliases": [  # List of aliases (Read-only)
            ],
        }

    def delete_from_gsuite(self) -> bool:
        """
        Used to delete the group from Gsuite. Use with caution.

        Returns:
            True if successful, else False.
        """
        try:
            self.service.groups().delete(groupKey=self.id).execute()
            return True
        except:
            return False

    def hide_from_GAL(self) -> bool:
        """
        Hides the group from Global Address List and updates self.settings to reflect that.
        :return: True if successful
        """
        self.settings["includeInGlobalAddressList"] = False
        self.settings_service.groups().patch(groupUniqueId=self.email, body=self.settings).execute()
        return True

    def change_to_security_group(self) -> bool:
        """
        Updates group settings to match class default of security groups
        :return: True if patched
        """
        # TODO: Merge with change to DL and add param for what type of perms to use
        patch_needed = False
        for k, v in GoogleGroup.security_group_settings.items():
            if self.settings[k] != v and type(v) != bool or self.settings[k].lower() != str(
                    v).lower():  # second is for BOOL values
                print(f'Changing {self.settings[k]} to {v}')
                patch_needed = True
            self.settings[k] = v
        if patch_needed:
            self.settings_service.groups().patch(groupUniqueId=self.email, body=self.settings).execute()
        return patch_needed

    def change_to_distribution_list(self, allowPublic: bool = False) -> bool:
        """
        Updates group settings to match class default of distribution lists
        :param allowPublic: If true, allow public contact. If false, allow only internal email.
        :return: True if patched
        """
        patch_needed = False
        if allowPublic:
            settings = GoogleGroup.public_distribution_list_settings
        else:
            settings = GoogleGroup.internal_distribution_list_settings
        for k, v in settings.items():
            if self.settings[k] != v and type(v) != bool or self.settings[k].lower() != str(
                    v).lower():  # second is for BOOL values
                self.settings[k] = v
                patch_needed = True
        if patch_needed:
            self.settings_service.groups().patch(groupUniqueId=self.email, body=self.settings).execute()
        return patch_needed

    def patch(self) -> bool:
        """
        Updates group description
        :param update_dict: key value pairs you want to update
        :return: True if patched
        """
        patch_needed = False
        temp_json = GoogleGroup.get_from_gsuite(self.service, self.settings_service, self.email).jsonify()
        update_dict = self.jsonify()
        for k, v in update_dict.items():
            if temp_json[k] != v:
                patch_needed = True
        if patch_needed:
            result = self.service.groups().patch(groupKey=self.email, body=update_dict).execute()
        return patch_needed

    @staticmethod
    def get_from_gsuite(service, settings_service, id: str) -> GoogleGroup:
        """
        Used to create a GoogleGroup object if the group already exists.

        Args:
            service: GoogleDirectory().directory_service object that is used to connect to Google API.
            id: UUID or Email of the group you want to retrieve.

        Returns:
            The specified group.
        """
        _dict = service.groups().get(groupKey=id).execute()
        return GoogleGroup(service=service, settings_service=settings_service, group=_dict)

    @staticmethod
    def create_in_gsuite(service, settings_service, email: str, name: str, description: str,
                         inGAL: bool = True) -> GoogleGroup:
        """
        Used to create a new group in gsuite.

        Args:
            service: GoogleDirectory().directory_service. Used for connecting to Google API.
            email: The email address that should be used for the group. Must be unique.
            name: Name of the group.
            description: What is this group for? Why does it exist?
            inGAL: Does this group appear in the global address list/Directory? Defaults to true.

        Returns:
            A properly formatted GoogleGroup object representing the new group.
        """
        body = {
            "email": email,
            "name": name,
            "description": description,
        }
        service.groups().insert(body=body).execute()
        return GoogleGroup.get_from_gsuite(service, settings_service, email)

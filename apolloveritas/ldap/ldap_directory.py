from __future__ import annotations
from ldap3 import Server, Connection, ALL, SUBTREE, ObjectDef, LEVEL, MODIFY_REPLACE, MODIFY_DELETE, MODIFY_ADD
from json import load
from pathlib import Path
from typing import List, Dict, Union
import re

from apolloveritas.utils.utils import str_missing_key

# TODO: remove pattern of explicit return None
# TODO: implement custom exception handling

class LdapDirectory:
    """Represents the directory itself. Wrapper for ldap3. Class properties are pulled in from the config
    directory. Class props are passed in as default instance props.

    Args:
        server (str): hostname or IP address of the server.
        user (str): distinguishedName of the user that binds to the ldap server.
        password (str): that user's password.
        base_dn (str): OU we want to limit this program's access to.
        lazy_load (bool): If true, does not load users or groups and just establishes a connection.


    Attributes:
        users (List[LdapUser]): Sync-safe list of users.
        groups (List[LdapGroup]): Sync-safe list of groups.
        all_users (List[LdapUser]): ALL users in the domain, limited only by base_dn.
        all_groups (List[LdapGroup]): ALL groups in the domain, limited only by base_dn.
        host (str): hostname or ip address of the controller this code is running against.
        server (ldap3.Server): ldap3.Server: Domain Controller this class will interact with.
        user (str): User CN used for reading/writing data over LDAPS.
        password (str): Password for user.
        base_dn (str): OU we are limiting all access to. Searches include all children of this.
        exclusions (str): Contains a list of targets that will NOT be scanned. This includes children of base_dn.
        targets (str): dict: Contains a list of targets that must be scanned. Overrides exclusions.
        lazyLoaded (bool): Are users and groups loaded and cached? If this is true, we did not cache anything.

    Todo:
        multiple results error when expecting single results
        pull from google
        check UAC codes from https://support.microsoft.com/en-us/help/305144/how-to-use-useraccountcontrol-to-manipulate-user-account-properties
    """
    # TODO: redo configuration to environment variables
    config_filepath = Path(Path(__file__).parents[2], 'creds', 'ldap.json')
    with open(config_filepath, 'r') as config_file:
        config = load(config_file)
    host = config['host']
    # TODO: Allow configuration of ssl and port for people with bad security practices
    # TODO: Create helper script to configure ADCA and add a cert to the Domain Controller.
    server = Server(host, use_ssl=True, port=636, get_info=ALL)
    user = config['user']
    password = config['password']
    base_dn = config['base_dn']
    exclusion_filepath = Path(Path(__file__).parents[2], 'config', 'ldap_exclusions.json')
    with open(exclusion_filepath, 'r') as exclusion_file:
        exclusions = load(exclusion_file)
    target_filepath = Path(Path(__file__).parents[2], 'config', 'ldap_sync_targets.json')
    with open(target_filepath, 'r') as target_file:
        targets = load(target_file)

    def __init__(self, server=server, user=user, password=password, base_dn=base_dn, lazy_load: bool = False):
        self.conn = Connection(server,
                               user=user,
                               password=password,
                               auto_bind=True, )  #: Can be used to access python-ldap3 functions directly.
        self.excludedOrganizationalUnits = LdapDirectory.exclusions['organizationalUnits']
        self.excludedUsers = LdapDirectory.exclusions['users']
        self.excludedGroups = LdapDirectory.exclusions['groups']
        self.includedOrganizationalUnits = LdapDirectory.targets['organizationalUnits']
        self.includedUsers = LdapDirectory.targets['users']
        self.includedGroups = LdapDirectory.targets['groups']
        self.conn.bind()
        self.obj_user = ObjectDef('user', self.conn)
        self.obj_group = ObjectDef('group', self.conn)
        self.base_dn = base_dn
        self.lazyLoaded = lazy_load
        if not self.lazyLoaded:
            print('Loading all LDAP users, this may take awhile.')
            self.all_users: List[LdapUser] = self.get_all_users()
            self.users: List[LdapUser] = self.remove_excluded_users(self.all_users)
            self.disabled_users: List[LdapUser] = [user for user in self.all_users if user.userAccountControl == 514]
            self.all_groups: List[LdapGroup] = self.get_all_groups()
            self.groups: List[LdapGroup] = self.remove_excluded_groups(self.all_groups)

    def get_user_by_sam(self, sam: str) -> LdapUser | None:
        """
        Looks up a user by the field sAMAccountName

        Args:
            sam: sAMAccountName of the user you want to return. Must match exactly one user.

        Returns:
            Single user.
        """
        user_objects = []
        entry_generator = self.conn.extend.standard.paged_search(search_base=self.base_dn,
                                                                 search_filter=f'(&(objectclass=user)(sAMAccountName={sam}))',
                                                                 attributes=['*'],
                                                                 paged_size=1000,
                                                                 generator=True)
        for user in entry_generator:
            user_objects.append(LdapUser(user))
        if len(user_objects) == 1:
            return user_objects[0]
        else:
            return None

    def get_user_by_employeeid(self, employeeid: str) -> LdapUser | None:
        """
        Looks up a user by the field sAMAccountName

        Args:
            employeeid: sAMAccountName of the user you want to return. Must match exactly one user.

        Returns:
            Single user.
        """
        user_objects = []
        entry_generator = self.conn.extend.standard.paged_search(search_base=self.base_dn,
                                                                 search_filter=f'(&(objectclass=user)(employeeId={employeeid}))',
                                                                 attributes=['*'],
                                                                 paged_size=1000,
                                                                 generator=True)
        for user in entry_generator:
            user_objects.append(LdapUser(user))
        if len(user_objects) == 1:
            return user_objects[0]
        else:
            return None

    def get_user_by_mail(self, mail: str) -> LdapUser | None:
        """
        Looks up a user by the field sAMAccountName

        Args:
            mail: email of the user you want to return. Must match exactly one user.

        Returns:
            Single user.
        """
        user_objects = []
        entry_generator = self.conn.extend.standard.paged_search(search_base=self.base_dn,
                                                                 search_filter=f'(&(objectclass=user)(mail={mail}))',
                                                                 attributes=['*'],
                                                                 paged_size=1000,
                                                                 generator=True)
        for user in entry_generator:
            user_objects.append(LdapUser(user))
        if len(user_objects) == 1:
            return user_objects[0]
        else:
            return None

    def get_user_by_dn(self, dn: str) -> LdapUser | None:
        """
        Looks up a user by their distinguished name.

        Args:
            dn: distinguishedName of user. Must be exactly correct or returns none.

        Returns:
            Single User.
        """
        user_objects = []
        entry_generator = self.conn.extend.standard.paged_search(search_base=dn,
                                                                 search_filter='(objectclass=user)',
                                                                 attributes=['*'],
                                                                 paged_size=1,
                                                                 generator=True)
        for user in entry_generator:
            user_objects.append(LdapUser(user))
        if len(user_objects) > 1:
            print("More than one result obtained.")
            return None
        if len(user_objects) == 1:
            return user_objects[0]
        else:
            return None

    def get_cached_user_by_dn(self, dn: str) -> LdapUser:
        for user in self.all_users:
            if user.distinguishedName == dn:
                return user
        raise ValueError(dn)

    def get_cached_user_by_sam(self, sam: str) -> LdapUser:
        for user in self.all_users:
            if user.sAMAccountName == sam:
                return user
        # TODO: Refactor to return None or custom error
        raise ValueError(sam)

    def get_cached_user_by_employeeid(self, employeeid: str) -> LdapUser | None:
        employeeid = str(employeeid)  # ensures that integer values are converted to a string
        for user in self.all_users:
            if user.employeeId == employeeid:
                return user
        return None

    def get_all_users(self, ou: str = None, recurse: bool = True) -> List[LdapUser]:
        """
        Function to retrieve ALL users. Does not process exclusions.

        Args:
            ou (str): limit search to a specific OU. If not specified, searches from self.base_dn.
            recurse (bool): Should this function check the whole subtree?
        Returns:
             List[LdapUser]: List of all LdapUser objects in the domain

        """
        print("Loading all LDAP users. This may take awhile.")
        if not ou:
            ou = self.base_dn
        user_objects = []
        if recurse:
            search_scope = SUBTREE
        else:
            search_scope = LEVEL
        entry_generator = self.conn.extend.standard.paged_search(search_base=ou,
                                                                 search_filter='(objectclass=user)',
                                                                 search_scope=search_scope,
                                                                 attributes=['*'],
                                                                 paged_size=1000,
                                                                 generator=True)
        for user in entry_generator:
            user_objects.append(LdapUser(user))
        if len(user_objects) > 0:
            return user_objects
        return user_objects

    def new_user(self, user: LdapUser) -> LdapUser:
        """
        Creates a new user account. You must have specified at least first name and last name.
        User accounts have no password and are disabled by default due to limitations with Active Directory.

        Examples:
            How to create a user, set password, and enable the user.
            u = LdapUser(ldap_teacher_dict)
            u2 = d.new_user(u)
            d.reset_password(u2, 'censored for repo')
            u2.userAccountControl = 512
            d.modify_user(u2)

        Args:
            user: locally created LdapUser object.

        Returns:
            The created user.
        """
        # TODO: check for required keys by using d.server.schema.object_classes['user'] to find what it needs
        self.conn.add(
            user.distinguishedName,
            object_class=['person', 'user'],
            attributes=user.safeDict
        )
        return self.get_user_by_sam(user.sAMAccountName)

    def new_group(self, mocked_group: LdapGroup) -> LdapGroup:
        existing_group = self.get_group_by_sam(mocked_group.sAMAccountName)
        if existing_group:
            return existing_group
        self.conn.add(
            mocked_group.distinguishedName,
            object_class=['group'],
            attributes=mocked_group.safeDict
        )
        new_group = self.get_group_by_sam(mocked_group.sAMAccountName)
        if new_group:
            print(f'Made new group: {mocked_group.sAMAccountName}')
            return new_group
        else:
            raise ValueError

    def reset_password(self, user: LdapUser, password: str):
        """
        Helper method to reset a user's password because this command is weird.
        Args:
            user: LdapUser object whose password you wish to reset.
            password: plaintext password string you wish to change their password to

        Returns:
            ODO: confirm what this returns. I think it's a bool.
        """
        return self.conn.extend.microsoft.modify_password(user.distinguishedName, password)

    def remove_users_from_excluded_ou(self, users: List[LdapUser]) -> List[LdapUser]:
        """
        Helper function for remove_excluded users. Should not be called directly.

        Args:
            users: who to check for exclusions

        Returns:
            Safe list of users to sync.
        """
        user_list: List[LdapUser] = []
        for user in users:
            exclude = False
            for ou in self.excludedOrganizationalUnits:
                if ou in user.parent_ou and user.parent_ou not in self.includedOrganizationalUnits:
                    exclude = True
            if not exclude:
                user_list.append(user)
        return user_list

    def remove_excluded_users(self, users: List[LdapUser]) -> List[LdapUser]:
        """
        Removes users from list if they are in self.excludedUsers or self.excludedOrganizationalUnits

        Args:
            users: Those you'll check for exclusions

        Returns:
            Safe list of users to sync.
        """
        user_list: List[LdapUser] = []
        for user in users:
            if (user.cn not in self.excludedUsers
                    and user.sAMAccountName not in self.excludedUsers
                    and user.userAccountControl != 514):  # uac 514 means user is disabled
                user_list.append(user)
        user_list = self.remove_users_from_excluded_ou(user_list)
        return user_list

    def get_all_groups(self, ou: str = None, recurse: bool = True) -> List[LdapGroup]:
        """
        Method to retrieve ALL groups. Does not process exclusions.

        Args:
            ou: OU to limit this search to. If none, uses self.base_dn
            recurse: Should this include results from child OUs?

        Returns:
            ALL groups within that OU.
        """
        print("Loading all LDAP Groups. This may take awhile.")
        if not ou:
            ou = self.base_dn
        group_objects = []
        if recurse:
            search_scope = SUBTREE
        else:
            search_scope = LEVEL
        entry_generator = self.conn.extend.standard.paged_search(search_base=ou,
                                                                 search_filter='(objectclass=group)',
                                                                 search_scope=search_scope,
                                                                 attributes=['*'],
                                                                 paged_size=1000,
                                                                 generator=True)
        for group in entry_generator:
            group_objects.append(LdapGroup(group))
        if len(group_objects) > 0:
            return group_objects
        return group_objects

    def remove_groups_from_excluded_ou(self, groups: List[LdapGroup]) -> List[LdapGroup]:
        """
        Helper function for remove_excluded_groups. Should not be called directly.

        Args:
            groups: Unsafe list of groups.

        Returns:
            Sync-safe list of groups.
        """
        group_list: List[LdapGroup] = []
        for group in groups:
            exclude = False
            for ou in self.excludedOrganizationalUnits:
                if ou in group.parent_ou and ou not in self.includedOrganizationalUnits:
                    exclude = True
            if not exclude:
                group_list.append(group)
        return group_list

    def remove_excluded_groups(self, groups: List[LdapGroup]) -> List[LdapGroup]:
        """
        Used to ensure a list of groups is safe to sync to Google Workspace or other targets.

        Args:
            groups: list of groups you want to check

        Returns:
            Sync-safe list of groups.
        """
        group_list: List[LdapGroup] = []
        for group in groups:
            if (group.cn not in self.excludedGroups
                    and group.sAMAccountName not in self.excludedGroups):
                group_list.append(group)
        group_list = self.remove_groups_from_excluded_ou(group_list)
        return group_list

    def get_group_by_sam(self, sam: str) -> LdapGroup | None:
        """
        Method used to get a single group by sAMAccountName. Must be exact.
        Args:
            sam: sAMAccountName of group you want to retrieve.

        Returns:
            Single group.
        """
        group_objects = []
        entry_generator = self.conn.extend.standard.paged_search(search_base=self.base_dn,
                                                                 search_filter=f'(&(objectclass=group)(sAMAccountName={sam}))',
                                                                 attributes=['*'],
                                                                 paged_size=1000,
                                                                 generator=True)
        for group in entry_generator:
            group_objects.append(LdapGroup(group))
        if len(group_objects) == 1:
            return group_objects[0]
        else:
            # todo replace with group not found error
            return None

    def get_group_by_dn(self, dn: str) -> LdapGroup | None:
        """
        Looks up a group by their distinguished name.

        Args:
            dn: distinguishedName of group. Must be exactly correct or returns none.

        Returns:
            Single Group.
        """
        group_objects = []
        entry_generator = self.conn.extend.standard.paged_search(search_base=dn,
                                                                 search_filter='(objectclass=group)',
                                                                 attributes=['*'],
                                                                 paged_size=1,
                                                                 generator=True)
        for group in entry_generator:
            group_objects.append(LdapGroup(group))
        if len(group_objects) > 1:
            print("More than one result obtained.")
            return None
        if len(group_objects) == 1:
            return group_objects[0]
        else:
            return None

    def get_cached_group_by_dn(self, dn: str) -> LdapGroup:
        for group in self.groups:
            if group.distinguishedName == dn:
                return group
        raise ValueError(dn)

    def get_cached_group_by_sam(self, sam: str) -> LdapGroup:
        for group in self.groups:
            if group.sAMAccountName == sam:
                return group
        raise ValueError(sam)

    def get_all_values_of_attribute(self, attribute: str) -> List:
        """
        Helper method to get a complete list of all values for a given user attribute.

        Args:
            attribute: a valid LdapUser attribute.

        Returns:
            All possible values of that attribute within the directory.
        """
        values = []
        for user in self.all_users:
            if user.__getattribute__(attribute) not in values:
                values.append(user.__getattribute__(attribute))
        return values

    def objectify_members(self, member_dns: List[str]) -> List[Union[LdapGroup, LdapUser]]:
        """
        Converts a group.memberOf list into a list of objects.
        :param member_dns: LdapGroup.memberOf
        :return: list of LdapGroups and LdapUsers
        """
        member_objects = []
        for member in member_dns:
            try:
                member_object = self.get_cached_group_by_dn(member)
            except ValueError:
                try:
                    member_object = self.get_cached_user_by_dn(member)
                except ValueError:
                    raise ValueError
            if member_object:
                member_objects.append(member_object)
        return member_objects

    def get_nested_member_users(self, members: List[Union[LdapGroup, LdapUser]], name) -> List[LdapUser]:
        # TODO: Replace this with the method from ldap3 using the magic AD method
        while True:
            group_in_members = False
            print(f'Starting nested member loop for {name}.')
            for member in members:
                if type(member) == LdapGroup:
                    group_in_members = True
            if not group_in_members:
                return members
            for member in members:
                if type(member) == LdapGroup:
                    if member.members:
                        nested_members = self.objectify_members(member.members)
                        members.remove(member)
                        for nested_member in nested_members:
                            members.append(nested_member)
                    else:
                        members.remove(member)


class LdapUser:
    """Represents a single LDAP User account. Should be created using LdapDirectory.get_user methods.

    Args:
        ldap_dict (dict): Must contain subdict 'Attributes'. Obtained by calls made from LdapDirectory get_user methods
            and generally should not be manually created.

    Todo:
        refactor naming convention to googleStyle
        methods - add/remove members, add to group, remove from group, alter fields
    """

    def __init__(self, ldap_dict):
        try:
            self.dict = ldap_dict['attributes']
        except KeyError:
            self.dict = ldap_dict
        self.accountExpires = None  #: Timestamp of when account expires.
        self.badPasswordTime = None  #:
        self.badPwdCount = None  #:
        self.cn = None  #: Common Name
        self.codePage = None  #:
        self.company = None  #:
        self.countryCode = None  #:
        self.dSCorePropagationData = None  #:
        self.department = None  #:
        self.description = None  #:
        self.displayName = None  #:
        self.distinguishedName = None  #: Full DN of the object. Unique per user.
        self.employeeId = None  #:
        self.givenName = None  #: First Name
        self.instanceType = None  #:
        self.lastLogoff = None  #:
        self.lastLogon = None  #:
        self.logon_count = None  #:
        self.mail = None  #: Email
        self.memberOf = None  #: Groups this user is a member of.
        self.name = None  #:
        self.objectCategory = None  #:
        self.objectClass = None  #:
        self.objectGUID = None  #:
        self.objectSid = None  #:
        self.physicalDeliveryOfficeName = None  #: "Office" field in AD.
        self.primaryGroupId = None  #:
        self.pwdLastSet = None  #:
        self.sAMAccountName = None  #:
        self.sAMAccountType = None  #:
        self.sn = None  #: Last Name
        self.title = None  #:
        self.uSNChanged = None  #:
        self.uSNCreated = None  #:
        self.userAccountControl = None  #: support.microsoft.com/en-us/help/305144/how-to-use-useraccountcontrol-to-manipulate-user-account-properties
        self.userPrincipalName = None  #:
        self.whenChanged = None  #:
        self.whenCreated = None  #:
        self.userPassword = None  #:
        self.fill_attrs_from_dict()
        try:
            self.parent_ou = self.distinguishedName[
                             (4 + len(self.cn)):]  #: removes "CN={cn}," from distinguishedName to get full OU
            self.direct_parent_ou_name = re.findall(r'OU=(.+?),',
                                                    self.parent_ou)  #: gets the content between OU and comma and returns a list of values
        except TypeError:
            self.parent_ou = None
        self.safeDict = self.get_safe_dict()

    def fill_attrs_from_dict(self):
        """
        Helper method to fill attributes. Fills anything missing from self.dict with None.
        Should never be called directly, and should only be used by __init__.

        Returns:
            None. Updates self.
        """
        while True:
            try:
                self.accountExpires = self.dict['accountExpires']
                self.badPasswordTime = self.dict['badPasswordTime']
                self.badPwdCount = self.dict['badPwdCount']
                self.cn = self.dict['cn']
                self.codePage = self.dict['codePage']
                self.company = self.dict['company']  #:
                self.countryCode = self.dict['countryCode']
                self.dSCorePropagationData = self.dict['dSCorePropagationData']
                self.department = self.dict['department']
                self.description = self.dict['description']
                if type(self.description) == list:
                    self.description = self.description[0]
                self.displayName = self.dict['displayName']
                self.distinguishedName = self.dict['distinguishedName']
                self.employeeId = self.dict['employeeID']
                self.givenName = self.dict['givenName']
                self.instanceType = self.dict['instanceType']
                self.lastLogoff = self.dict['lastLogoff']
                self.lastLogon = self.dict['lastLogon']
                self.logon_count = self.dict['logonCount']
                self.mail = self.dict['mail']
                self.memberOf = self.dict['memberOf']
                self.name = self.dict['name']
                self.objectCategory = self.dict['objectCategory']
                self.objectClass = self.dict['objectClass']
                self.objectGUID = self.dict['objectGUID']
                self.objectSid = self.dict['objectSid']
                self.physicalDeliveryOfficeName = self.dict['physicalDeliveryOfficeName']
                self.primaryGroupId = self.dict['primaryGroupID']
                self.pwdLastSet = self.dict['pwdLastSet']
                self.sAMAccountName = self.dict['sAMAccountName']
                self.sAMAccountType = self.dict['sAMAccountType']
                self.sn = self.dict['sn']
                self.title = self.dict['title']
                self.uSNChanged = self.dict['uSNChanged']
                self.uSNCreated = self.dict['uSNCreated']
                self.userAccountControl = self.dict['userAccountControl']
                self.userPrincipalName = self.dict['userPrincipalName']
                self.whenChanged = self.dict['whenChanged']
                self.whenCreated = self.dict['whenCreated']
                self.userPassword = self.dict['userPassword']
                break
            except KeyError as missing_key:
                self.dict[str_missing_key(missing_key)] = None
                continue

    def get_safe_dict(self) -> Dict:
        """
        Helper method to generate a version of the user's attributes without attributes that are None.

        Returns:
            Dict containing all keys that have a value.
        """
        safe_dict = {}
        for k, v in self.__dict__.items():
            if v is not None and k != 'dict':
                safe_dict[k] = v
        if 'parent_ou' in safe_dict.keys():
            safe_dict.pop('parent_ou')
        if 'direct_parent_ou_name' in safe_dict.keys():
            safe_dict.pop('direct_parent_ou_name')
        return safe_dict

    def modify(self) -> LdapUser:
        """
        Compares a user object to that user in the live directory and pushes changes to the directory.
        If changes are detected that are not safe to change via this method, it should raise an unsafeChange exception.
        That exception should contain the attributes and values you wanted to change as a dict.

        Returns:
            The user after changes have been made. Freshly pulled from the directory.
        """
        # TODO: move safe_to_change to a configuration file
        safe_to_change = ['givenName', 'sn', 'userAccountControl', 'company', 'title', 'department', 'description']
        d = LdapDirectory(lazy_load=True)
        ldap_user = d.get_user_by_sam(self.sAMAccountName)
        for k, v in self.__dict__.items():
            if ldap_user.__getattribute__(k) != v and k in safe_to_change:
                if ldap_user.__getattribute__(k) is not None and v is not None:
                    d.conn.modify(self.distinguishedName,
                                  {k: [(MODIFY_REPLACE, [v])]})
                if ldap_user.__getattribute__(k) is None and v is not None:
                    d.conn.modify(self.distinguishedName,
                                  {k: [(MODIFY_ADD, [v])]})
                if ldap_user.__getattribute__(k) is not None and v is None:
                    d.conn.modify(self.distinguishedName,
                                  {k: [(MODIFY_DELETE, [v])]})
            elif ldap_user.__getattribute__(k) != v and k not in safe_to_change:
                # todo Raise unsafe attribute error
                pass
        return d.get_user_by_sam(self.sAMAccountName)


class LdapGroup:
    """Represents a single LDAP Group. Should be obtained by using LdapDirectory get_group methods.

    Args:
        ldap_dict (dict): Must contain subdict 'Attributes'. Obtained by calls made from LdapDirectory get_group methods
            and generally should not be manually created.

    Todo:
        refactor naming convention to googleStyle
        methods - Reset password? add to group, remove from group, enable/disable/ alter fields
    """

    def __init__(self, ldap_dict):
        try:
            self.dict = ldap_dict['attributes']
        except KeyError:
            self.dict = ldap_dict
        self.distinguishedName = None  #: distinguished Name
        self.description = None  #: description
        self.cn = None  #: Common Name
        self.groupType = None  #: explained at: https://docs.microsoft.com/en-us/windows/win32/adschema/a-grouptype
        self.instanceType = None  #:
        self.info = None  #:
        self.members = None  #: Who is in the group?
        self.memberOf = None  #: What groups is this one a member of?
        self.name = None  #:
        self.mail = None  #: Email
        self.objectCategory = None  #:
        self.objectClass = None  #:
        self.objectGUID = None  #:
        self.objectSid = None  #:
        self.sAMAccountName = None  #:
        self.sAMAccountType = None  #:
        self.uSNChanged = None  #:
        self.uSNCreated = None  #:
        self.whenChanged = None  #:
        self.whenCreated = None  #:
        self.fill_from_dict()
        try:
            self.parent_ou = self.distinguishedName[
                             (4 + len(self.cn)):]  #: removes "CN={cn}," from distinguishedName to get full OU
            self.direct_parent_ou_name = re.findall(r'OU=(.+?),',
                                                    self.parent_ou)  #: gets the content between OU and comma and returns a list of values
        except TypeError:
            self.parent_ou = None
        self.safeDict = self.get_safe_dict()

    def fill_from_dict(self):
        """
        Helper method to fill attributes. Fills anything missing from self.dict with None.
        Should never be called directly, and should only be used by __init__.

        Returns:
            None. Updates self.
        """
        while True:
            try:
                self.distinguishedName = self.dict['distinguishedName']
                self.description = self.dict['description']
                if type(self.description) == list:
                    self.description = self.description[0]
                self.cn = self.dict['cn']
                self.groupType = self.dict['groupType']
                self.instanceType = self.dict['instanceType']
                self.members = self.dict['member']  # todo make this ldap user or group objects
                self.info = self.dict['info']
                self.memberOf = self.dict['memberOf']  # todo make this ldap group objects
                self.name = self.dict['name']
                self.mail = self.dict['mail']
                self.objectCategory = self.dict['objectCategory']
                self.objectClass = self.dict['objectClass']
                self.objectGUID = self.dict['objectGUID']
                self.objectSid = self.dict['objectSid']
                self.sAMAccountName = self.dict['sAMAccountName']
                self.sAMAccountType = self.dict['sAMAccountType']
                self.uSNChanged = self.dict['USNChanged']
                self.uSNCreated = self.dict['uSNCreated']
                self.whenChanged = self.dict['whenChanged']
                self.whenCreated = self.dict['whenChanged']
                break
            except KeyError as missing_key:
                self.dict[str_missing_key(missing_key)] = None
                continue

    def add_member(self, members: List[Union[LdapUser, LdapGroup]]) -> bool:
        """
        Adds a members to this group.

        Args:
            members: A list of LdapUser objects. Must be a list, even if one user.

        Returns:
            True if successful else false.
        """
        d = LdapDirectory(lazy_load=True)
        member_dns = [user.distinguishedName for user in members]
        result = d.conn.extend.microsoft.add_members_to_groups(members=member_dns,
                                                               groups=self.distinguishedName)
        return result

    def remove_member(self, members: List[Union[LdapUser, LdapGroup]]) -> bool:
        """
        Removes a members from this group.

        Args:
            members: A list of LdapUser objects. Must be a list, even if one user.

        Returns:
            True if successful else false.
        """
        d = LdapDirectory(lazy_load=True)
        member_dns = [user.distinguishedName for user in members]
        result = d.conn.extend.microsoft.remove_members_from_groups(members=member_dns,
                                                                    groups=self.distinguishedName)
        return result

    def get_safe_dict(self) -> Dict:
        """
        Helper method to generate a version of the user's attributes without attributes that are None.

        Returns:
            Dict containing all keys that have a value.
        """
        safe_dict = {}
        for k, v in self.__dict__.items():
            if v is not None and k != 'dict':
                safe_dict[k] = v
        if 'parent_ou' in safe_dict.keys():
            safe_dict.pop('parent_ou')
        if 'direct_parent_ou_name' in safe_dict.keys():
            safe_dict.pop('direct_parent_ou_name')
        return safe_dict

    def modify(self) -> LdapGroup:
        """
        Compares a group object to that group in the live directory and pushes changes to the directory.
        If changes are detected that are not safe to change via this method it should raise an unsafeChange exception.
        That exception should contain the attributes and values you wanted to change as a dict.

        Returns:
            The group after changes have been made. Freshly pulled from the directory.
        """
        safe_to_change = ['groupType', 'description']
        d = LdapDirectory(lazy_load=True)
        ldap_group = d.get_group_by_sam(self.sAMAccountName)
        for k, v in self.__dict__.items():
            if ldap_group.__getattribute__(k) != v and k in safe_to_change:
                if ldap_group.__getattribute__(k) is not None and v is not None:
                    d.conn.modify(self.distinguishedName,
                                  {k: [(MODIFY_REPLACE, [v])]})
                if ldap_group.__getattribute__(k) is None and v is not None:
                    d.conn.modify(self.distinguishedName,
                                  {k: [(MODIFY_ADD, [v])]})
                if ldap_group.__getattribute__(k) is not None and v is None:
                    d.conn.modify(self.distinguishedName,
                                  {k: [(MODIFY_DELETE, [v])]})
            elif ldap_group.__getattribute__(k) != v and k not in safe_to_change:
                # todo Raise unsafe attribute error
                pass
        return d.get_group_by_sam(self.sAMAccountName)

    # TODO: Methods (see google group to know what to add)


class LdapComputer:
    pass
    # TODO: Create LdapComputer methods

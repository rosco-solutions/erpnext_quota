import frappe
from frappe import _
from frappe.utils.data import today, date_diff, get_datetime_str
import json

def successful_login(login_manager):
    """
    on_login verify if site is not expired
    """
    with open(frappe.get_site_path('quota.json')) as jsonfile:
        parsed = json.load(jsonfile)
    
    valid_till = parsed['valid_till']
    diff = date_diff(valid_till, today())
    if diff < 0:
        frappe.throw(_("You site is suspended. Please contact Sales"), frappe.AuthenticationError)

    #validate concurrent logins
    try:
        allowed_concurrent_users = parsed['concurrent_users']

        # Loop through the concurrent user settings and find out how many users are logged in with the role specified.
        values = {'user':login_manager.user}
        userroles = frappe.db.sql(  """ SELECT HR.role 
                                        FROM `tabHas Role` HR 
                                        WHERE HR.parent = %(user)s
                                    """,values=values)
        for acu in allowed_concurrent_users:
            if acu['role'] == '':
                # Check if there is a total number of concurrent users limit set that is independant of role
                concurrent_user_list = frappe.db.sql("""SELECT S.user FROM tabSessions S""")
                concurrent_users = len(concurrent_user_list)
                if concurrent_users >= acu['allowed']:
                    frappe.throw(_('Sorry all login positions are taken. Please try again later to see if a login position has become available.'), frappe.AuthenticationError)                
            else:
                # Need to check if the current user has a role that has a restricted number of concurrent users. 
                # If they do then need to check for concurrent users.
                test = 0
                for myrole in userroles:
                    if myrole[0] == acu['role']:
                        test = 1
                        break
                if test == 1:
                    concurrent_user_list = frappe.db.sql("""SELECT  S.user
                                                        FROM    tabSessions S
                                                        INNER JOIN 
                                                                `tabHas Role` HR ON S.user = HR.parent
                                                        WHERE   HR.role = %(role)s
                                                        """,values=acu)
                    concurrent_users = len(concurrent_user_list)
                    if concurrent_users >= acu['allowed']:
                        frappe.throw(_('Sorry all login positions are taken for the ' + acu['role'] + ' role. Please try again later to see if a login position has become available.'), frappe.AuthenticationError)        
    except KeyError:
        pass

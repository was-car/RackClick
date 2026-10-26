"""Synthetic historical writer shapes for GUI50; not HTTP commands or real QA data."""
import uuid


def administrative_events(house, actor, customer):
    target, group, grant, session = [str(uuid.uuid4()) for _ in range(4)]
    username, name = '\ufeffLegacy e\u0301 <img> 😀', 'Grupo Ω <img> 😀'
    user = {'id': target, 'userName': username, 'active': True}
    member = {'groupId': group, 'userId': target, 'assigned': False}
    client_member = {'groupId': group, 'customerId': customer, 'assigned': True}
    permission = {'groupId': group, 'grantId': grant, 'capability': 'inventory.read', 'scope': 'customer', 'targetId': customer, 'assigned': False}
    revoke = {'userId': actor, 'sessionId': session}
    field = lambda key, kind, before, after: {'field': key, 'type': kind, 'before': before, 'after': after}
    cases = [
        ('user.create', target, None, user, [field('userId','uuid',None,target),field('userName','userName',None,username),field('active','boolean',None,'true')]),
        ('userGroup.create', group, None, {'id':group,'name':name,'kind':'userGroup'}, [field('groupId','uuid',None,group),field('name','name',None,name),field('groupKind','groupKind',None,'userGroup')]),
        ('customerGroup.create', group, None, {'id':group,'name':name,'kind':'customerGroup'}, [field('groupId','uuid',None,group),field('name','name',None,name),field('groupKind','groupKind',None,'customerGroup')]),
        ('userGroup.member.set', group, member, member | {'assigned':True}, [field('groupId','uuid',group,group),field('userId','uuid',target,target),field('assigned','boolean','false','true')]),
        ('customerGroup.member.set', group, client_member, client_member | {'assigned':False}, [field('groupId','uuid',group,group),field('customerId','uuid',customer,customer),field('assigned','boolean','true','false')]),
        ('userGroup.grant.set', group, permission, permission | {'assigned':True}, [field('groupId','uuid',group,group),field('grantId','uuid',grant,grant),field('capability','capability','inventory.read','inventory.read'),field('scope','scope','customer','customer'),field('targetId','uuid',customer,customer),field('assigned','boolean','false','true')]),
        ('user.state.set', target, user, user | {'active':False}, [field('userId','uuid',target,target),field('userName','userName',username,username),field('active','boolean','true','false')]),
        ('user.password.reset', target, user, user | {'passwordReset':True}, [field('userId','uuid',target,target),field('userName','userName',username,username),field('active','boolean','true','true'),field('passwordReset','boolean',None,'true')]),
        ('user.session.revoke', session, revoke, revoke | {'revoked':True,'wasCurrent':True}, [field('userId','uuid',actor,actor),field('sessionId','uuid',session,session),field('revoked','boolean',None,'true'),field('wasCurrent','boolean',None,'true')])
    ]
    result = []
    for action, resource, before, after, fields in cases:
        result.append({'action':action,'resource':resource,'before':before,'after':after,'request':str(uuid.uuid4()),'fields':fields})
        request = str(uuid.uuid4())
        cancel_fields = [field('requestId','uuid',None,request),field('state','state',None,'cancelled')]
        cancel_before = None
        if action == 'user.session.revoke':
            cancel_before = revoke
            cancel_fields = [field('userId','uuid',actor,None),field('sessionId','uuid',session,None)] + cancel_fields
        result.append({'action':action+'.cancel','resource':house if action.endswith('.create') else resource,
                       'before':cancel_before,'after':{'requestId':request,'state':'cancelled','operation':None},
                       'request':request,'fields':cancel_fields})
    return result

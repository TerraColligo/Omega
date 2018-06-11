from odoo import models, fields,api
from odoo.exceptions import Warning

class execute_code(models.Model):
    _name = 'execute.code'
    
    name = fields.Char('Name')
    query_text = fields.Text('Query Text')
    result_text = fields.Text('Result')
    
    @api.multi
    def execute_code(self):
        if self.query_text:
            localdict = {
                        'self':self, 
                        'cr': self._cr,
                        'uid': self._uid,
                        'result': None, #used to store the result of the test
                        'context': self._context or {},
                        'user':self.env.user
                        }
            #try:
            exec(self.query_text, localdict)
            #result = eval(self.query_text, localdict)
            self.write({'result_text':localdict.get('result','')})
#             except Exception, e:
#                 raise Warning(str(e))
        return True           
    

"""Pure, missing-only presentation updates for checked canonical revisions.

The caller supplies separately validated same-ID revisions. Existing figure,
caption, apparatus, product-context and authored presentation objects survive.
Only exact record hash references and newly reported measurements are added.
"""
import copy
import math


def rebind_record_refs(value,replacements):
    """Map exact data-path + old hash to new hash; unrelated content is copied."""
    count=0
    def visit(node):
        nonlocal count
        if isinstance(node,dict):
            out={key:visit(item) for key,item in node.items()}
            path=node.get('data_path')
            if path in replacements:
                before,after=replacements[path]
                if node.get('input_sha256')!=before:
                    raise ValueError('Existing Reader record reference does not bind its baseline')
                out['input_sha256']=after;count+=1
            return out
        if isinstance(node,list):return [visit(item) for item in node]
        return copy.deepcopy(node)
    return visit(value),count


def append_measurements(view,old,new,record_sha256):
    if old['record_id']!=new['record_id']:raise ValueError('Record identity differs')
    rid=new['record_id'];prior={m['id'] for m in old.get('measurements',[])}
    out=copy.deepcopy(view);added=[]
    for index,item in enumerate(new.get('measurements',[])):
        if item['id'] in prior:continue
        value=item['value'];number=value.get('value');unit=value.get('unit')
        if (value.get('status')!='reported' or not isinstance(number,(int,float))
            or isinstance(number,bool) or not math.isfinite(number) or not isinstance(unit,str)):
            raise ValueError('New measurement needs its exact reported numeric value and unit')
        row={'label':item['property'].replace('_',' ').capitalize(),
             'value':f'{number:g} {unit}'.strip(),'scope':f'{item["technique"]}; as stated for this product.',
             'sample_id':item['sample_id'],'status':'reported',
             'source':{'data_path':f'data/records/{rid}.json','json_pointer':f'/measurements/{index}/value','input_sha256':record_sha256},
             'source_locator':copy.deepcopy(item['evidence']),'record_id':rid,
             'kind':'measurement','measurement_id':item['id']}
        for key in ('productFacts','allProductFacts'):
            table=out.setdefault(key,[])
            if not isinstance(table,list):raise ValueError('Existing Reader facts are not a list')
            if any(f.get('measurement_id')==item['id'] and f.get('record_id')==rid for f in table):
                raise ValueError('New canonical measurement already has an unrelated presentation claim')
            table.append(copy.deepcopy(row))
        added.append(item['id'])
    return out,added


def rebind_protocol(binding,old,new,before_sha256,after_sha256):
    if binding.get('record_id')!=old['record_id'] or old['record_id']!=new['record_id']:
        raise ValueError('Protocol record identity differs')
    if binding.get('source_record_sha256')!=before_sha256:
        raise ValueError('Protocol does not bind the baseline record')
    if not {b['operation_id'] for b in binding.get('bindings',[])}<={o['id'] for o in new['operations']}:
        raise ValueError('Existing protocol artwork would lose its operation')
    return {**copy.deepcopy(binding),'source_record_sha256':after_sha256}

import sys
sys.path.insert(0, 'notebooks')
from soriana_02 import scrape_soriana_total
datos = scrape_soriana_total('Todo')
print('\n=== ' + str(len(datos)) + ' PRODUCTOS EXTRAIDOS ===\n')
for i, item in enumerate(datos, 1):
    print(str(i) + '. ' + item['producto'][:35] + ' - ' + item['categoria'][:12] + ' - ' + item['tienda'] + ' - PID: ' + item['pid_origen'][:10] + ' - $ ' + str(item['precio']))
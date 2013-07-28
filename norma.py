#

# No se pueden definir macros dentro de macros
# No se pueden definir macros mas de una vez, ni con nombres reservados
# Las macros no pueden usar macros que no hayan sido previamente definidas (y por ende no puede haber tampoco refs. circulares)
# Una macro no puede llamarse a si misma
# Espacio de memoria de DATOS (para variables locales) a partir de 0xF000 y hasta 0xFFFC (4093 direcciones)

# Como NORMA solo funciona con NORs, la idea es tomar el archivo de entrada y traducir todo a NORs.
# El traductor primero toma las macros y almacena su codigo y luego al recorrer el codigo en si mismo, lo traduce a NORs que pueden ser ejecutados por cpu()

debug = False

TAM_MEMORIA = 0xFFFF

def nor(a, b):
    return ~(a | b) & TAM_MEMORIA

mem = [0] * (TAM_MEMORIA + 1)

IP = 0xFFFF
SR = 0xFFFE
OUT = 0xFFFD

DATA = 0xF000

# array de palabras reservadas
reserved = ["local", "set", "label", "macro", "endm"]
# array de nombres de vars locales (strings)
locales = []
# array de nombres de labels (dicts con keys 'name' (nombre del label) y 'ip' (dir a poner a IP cuando se usen))
labels = []
# array de macros a expandir durante load (dicts con keys 'name' (nombre de la macro), 'args' (list de nombres de args) y 'body' (list de lineas de codigo))
macros = []
# array con variables locales (creo que sobra)
# data = []
# valor de ip conforme se traduce el programa a memoria
ip = 0

# Convierte una palabra a:
# - numero de direccion predefinida en memoria (IP, SR, OUT, DATA, ...)
# - numero de direccion valida en memoria
# - nombre de variable local (a valor en memoria de datos donde reside esa variable)
# - nombre de label (a valor de IP apuntada por la label)
def convierte(palabra):

    if palabra in ["IP", "SR", "OUT", "DATA"]:
        import sys
        return sys.modules[__name__].__getattribute__(palabra)
 
    try:
        addr = int(palabra)
        if addr < 0 or addr > ( len(mem) - 1 ):
            raise Exception("Direccion de memoria invalida")
    except (ValueError, IndexError) as direrr:
        try:
            addr = int(DATA + locales.index(palabra))
            mem[addr]
        except (ValueError, IndexError) as locerr:
            try:
                etiquetas = [ l['name'] for l in labels ]
                addr = int(labels[etiquetas.index(palabra)]['ip'])
                mem[addr]
            except (ValueError, IndexError) as laberr:
                raise Exception("La palabra '%s' no pudo ser convertida" % palabra)
    return addr

# Traduce una linea de codigo a lineas N1, N2, N3 donde Nn son direcciones de memoria
# - puesto que encuentra llamadas a macros, llama recursivamente a esta funcion para conseguir N1,N2,N3
def traduce(codigo):
    global ip

    if codigo[0] == "local": # reservar memoria para variable y mapear nombre
        for local in codigo[1:] :
            locales.append(local)
#            data.append(0)

    elif codigo[0] == "set": # asignar valor a variable mapeada o direccion
        setstr = codigo[1:]
        try:
            setval = int(setstr[0])
        except ValueError as verr: # NORMA permite usar hexadecimales en valores literales! :-D
            setval = int(setstr[0], 16)
        setdir = setstr[1] # la direccion puede ser una local ya declarada o una direccion en memoria a usar directamente
        try:
#            data[locales.index(setdir)] = setval
            mem[DATA + locales.index(setdir)] = setval
        except ValueError as verr:
            try:
                mem[int(setdir)] = setval
            except ValueError as verr:
                raise Exception("'%s' no es una variable definida" % setdir)
            except IndexError as ierr:
                raise Exception("La direccion '%s' esta fuera de rango" % setdir)

    elif codigo[0] == "label": # guardar direccion de memoria en memoria de labels
        labels.append({'name':codigo[1], 'ip':ip})

    elif codigo[0] in [ m['name'] for m in macros ]: # tomar funcion ya definida y guardar sus instrucciones en memoria tomando sus argumentos

        macro = [ m for m in macros if m['name'] == codigo[0] ][0]
        args = codigo[1:]
        for linea in macro['body']:
            line = linea[:]
            for n,arg in enumerate(macro['args']):
                for i,l in enumerate(line):
                    if l == arg:
                        line[i]=args[n]
            try:
                traduce(line)
            except Exception as ex:
                raise Exception("Macro %s: %s" % (macro['name'], ex))

    else: # nor (el objetivo del loader es 'aplanar' todo el codigo a estos bichos en mem)
        mem[ip] = convierte(codigo[0])
        mem[ip + 1] = convierte(codigo[1])
        mem[ip + 2] = convierte(codigo[2])
        ip += 3

# Carga el archivo con el programa y recorre linea a linea, cargando macros y traduciendo codigo a NORs en memoria
def loader(nomarchivo):
    
    archivo = open(nomarchivo)
    lineas = archivo.readlines()
    archivo.close()

    inmacro = ""
    for num, linea in enumerate(lineas):
        p = [ e for e in linea.strip().split(";")[0].strip().replace(","," ").split(" ") if e is not "" ]
        if not p:
            continue

        if debug: print "%s" % num, " ".join(p)
        if p[0] == "macro": # leer lineas de macro y guardar como funcion definida
            if inmacro:
                raise Exception("No puedes definir una macro dentro de otra macro")
            if p[1] in [ m['name'] for m in macros ]:
                raise Exception("Macro '%s' ya estaba previamente definida" % p[1])
            if p[1] in reserved:
                raise Exception("El nombre '%s' para la macro es una palabra reservada" % p[1])

            inmacro = p[1]
            macro = {}
            macro['name'] = p[1]
            macro['args'] = []
            try:
                for arg in p[2:] :
                    macro['args'].append(arg)
            except IndexError as ierr:
                pass
            macro['body'] = []
            macros.append(macro)
        elif p[0] == "endm":
            inmacro = ""
            continue
        elif inmacro:
            if p[0] == macros[-1]['name']:
                raise Exception("La macro %s se llama a si misma" % p[0])

            macros[-1]['body'].append(p)

        # Traduce linea para conseguir NORs en la memoria
        if not inmacro:
            traduce(p)

    if inmacro:
        raise Exception("No se encontro 'endm' para la macro %s" % inmacro)


    return mem


# Ejecuta lo que haya en memoria como NORs de 3 en 3 direcciones
def cpu(archivo):
    mem = loader(archivo)

    mem[IP] = 0

    # Como todo se tradujo a nors, el cpu es sencillisimo
    while True:
        i = mem[IP]
        a = mem[mem[i+0]]
        b = mem[mem[i+1]]
        r = mem[i+2]
        mem[IP] = i + 3
        f = nor(a, b)
        mem[r] = f
        mem[SR] = ((f >> 15) & 1) | ((f & 0x7FFF) << 1)
        if mem[IP] >= DATA:
            break

    print mem[OUT]


# main
if __name__ == "__main__":
    import getopt, sys

    archivo = "test.a" 
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:d:", ["file=","debug"])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(2)
    for o,a in sorted(opts):
        if o in ("-f", "--file"):
            archivo = a
        elif o in ("-d", "--debug"):
            debug = True

    cpu(archivo)

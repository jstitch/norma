#!/usr/bin/pyrg
# coding: utf-8

import unittest

import norma


class TestConvierte(unittest.TestCase):
    def test_01_dirpredefinida(self):
        self.assertEqual(norma.convierte("IP"), norma.IP)
        self.assertEqual(norma.convierte("SR"), norma.SR)
        self.assertEqual(norma.convierte("OUT"), norma.OUT)
        self.assertEqual(norma.convierte("DATA"), norma.DATA)

    def test_02_dirnumerica(self):
        self.assertEqual(norma.convierte("1000"), 1000)
        self.assertRaisesRegexp(Exception, "Direccion de memoria invalida", norma.convierte, **{'palabra': str(norma.TAM_MEMORIA + 1)})
        self.assertRaisesRegexp(Exception, "Direccion de memoria invalida", norma.convierte, **{'palabra': "-1"})

    def test_03_dirlocal(self):
        norma.locales.append("varlocal")
        self.assertEqual(norma.convierte("varlocal"), norma.DATA)
        norma.locales.append("varlocal2")
        self.assertEqual(norma.convierte("varlocal2"), norma.DATA + 1)
        norma.locales.append("varlocal3")
        norma.locales.append("varlocal4")
        norma.locales.append("varlocal5")
        self.assertEqual(norma.convierte("varlocal5"), norma.DATA + 4)

    def test_04_dirlabel(self):
        norma.labels.append({'name': "label1", 'ip': 1001})
        self.assertEqual(norma.convierte("label1"), 1001)
        norma.labels.append({'name': "label2", 'ip': norma.IP})
        self.assertEqual(norma.convierte("label2"), norma.IP)

    def test_05_direrronea(self):
        self.assertRaisesRegexp(Exception, "^La palabra '(\w+)' no pudo ser convertida$", norma.convierte, **{'palabra': "SPAM"})


class TestTraduce(unittest.TestCase):
    def setUp(self):
        reload(norma)

    def test_01_nor(self):
        self.assertEqual(norma.ip, 0)
        self.assertListEqual(norma.mem[0:3], [0, 0, 0])
        norma.mem[1000] = 201
        norma.mem[1001] = 202
        norma.traduce(['1000','1001','1002'])
        self.assertEqual(norma.ip, 3)
        self.assertListEqual(norma.mem[0:3], [1000, 1001, 1002])

    def test_02_local(self):
        self.assertListEqual(norma.locales, [])
#        self.assertListEqual(norma.data, [])
        norma.traduce(['local','t1','t2'])
        self.assertListEqual(norma.locales, ['t1','t2'])
#        self.assertListEqual(norma.data, [0,0])
        norma.mem[1000] = 300
        norma.traduce(['1000','t1','t2'])
        self.assertListEqual(norma.mem[0:3], [1000,norma.DATA,norma.DATA+1])

    def test_03_set(self):
        self.assertEqual(norma.mem[1001],0)
        norma.traduce(['set',200,1001])
        self.assertEqual(norma.mem[1001],200)
        norma.traduce(['local','var'])
#        self.assertEqual(norma.data[0],0)
        norma.traduce(['set',200,'var'])
#        self.assertEqual(norma.data[0],200)
        self.assertEqual(norma.mem[norma.DATA], 200)
        self.assertRaisesRegexp(Exception, "^'(\w+)' no es una variable definida$", norma.traduce, **{'codigo': ['set',200,'var2']})
        self.assertRaisesRegexp(Exception, "^La direccion '(\d+)' esta fuera de rango$", norma.traduce, **{'codigo': ['set',200,norma.TAM_MEMORIA + 1000]})

    def test_04_label(self):
        self.assertListEqual(norma.labels, [])
        norma.traduce(['label', 'etiq1'])
        self.assertDictEqual(norma.labels[0],{'name':'etiq1','ip':0})
        norma.traduce(['1000','1001','1002'])
        norma.traduce(['label', 'etiq2'])
        self.assertDictEqual(norma.labels[1],{'name':'etiq2','ip':3})


class TestMacros(unittest.TestCase):
    def setUp(self):
        reload(norma)

    def test_01_carga(self):
        norma.loader("test/loadmacro.a")
        self.assertEqual(len(norma.macros), 3)
        self.assertDictEqual(norma.macros[0], {'name': 'NOT',
                                               'args': ['a','r'],
                                               'body': [['a', 'a', 'r']]})
        self.assertDictEqual(norma.macros[1], {'name': 'OR',
                                               'args': ['a','b','r'],
                                               'body': [['local', 't'], ['a', 'b', 't'], ['NOT', 't', 'r']]})
        self.assertDictEqual(norma.macros[2], {'name': 'SET',
                                               'args': ['a','b','r'],
                                               'body': [['local', 't'], ['set', 'a', 't'], ['a', 'b', 'r']]})

    def test_02_exceptions(self):
        self.assertRaisesRegexp(Exception, "No se encontro 'endm' para la macro (\w+)", norma.loader, **{'nomarchivo': 'test/noendm.a'})

        self.assertRaisesRegexp(Exception, "La macro (\w+) se llama a si misma", norma.loader, **{'nomarchivo': 'test/autorefmacro.a'})

        self.assertRaisesRegexp(Exception, "Macro '(\w+)' ya estaba previamente definida", norma.loader, **{'nomarchivo': 'test/redefmacro.a'})

        self.assertRaisesRegexp(Exception, "El nombre '(\w+)' para la macro es una palabra reservada", norma.loader, **{'nomarchivo': 'test/reserved_label.a'})
        self.assertRaisesRegexp(Exception, "El nombre '(\w+)' para la macro es una palabra reservada", norma.loader, **{'nomarchivo': 'test/reserved_local.a'})
        self.assertRaisesRegexp(Exception, "El nombre '(\w+)' para la macro es una palabra reservada", norma.loader, **{'nomarchivo': 'test/reserved_set.a'})
        self.assertRaisesRegexp(Exception, "El nombre '(\w+)' para la macro es una palabra reservada", norma.loader, **{'nomarchivo': 'test/reserved_macro.a'})
        self.assertRaisesRegexp(Exception, "El nombre '(\w+)' para la macro es una palabra reservada", norma.loader, **{'nomarchivo': 'test/reserved_endm.a'})

        self.assertRaisesRegexp(Exception, "No puedes definir una macro dentro de otra macro", norma.loader, **{'nomarchivo': 'test/inceptmacro.a'})
        
    def test_03_traduce01(self):
        norma.mem[1000] = 200
        norma.loader("test/simplemacro.a")
        self.assertListEqual(norma.mem[0:3], [1000, 1000, 1001])
        
    def test_04_traduce02(self):
        norma.loader("test/movmacro.a")
        self.assertListEqual(norma.mem[0:3], [1000, 1000, 1001]) # NOT 1000, 1001
        self.assertListEqual(norma.mem[3:6], [1001, 1001, norma.DATA]) # MOV 1001, 1002 -> OR 1001, 1001, 1002 (1er linea): 1001, 1001, t
        self.assertListEqual(norma.mem[6:9], [norma.DATA, norma.DATA, norma.OUT]) # MOV 1001, OUT -> OR 1001, 1001, OUT (2da linea): NOT t, OUT -> t, t, OUT
        self.assertListEqual(norma.mem[9:12], [1003, 1003, norma.IP]) # NOT 1003, IP
        self.assertListEqual(norma.mem[12:norma.DATA], [0]*(norma.DATA-12))
        self.assertListEqual(norma.mem[norma.DATA:norma.DATA + 1], [0])
        self.assertListEqual(norma.mem[norma.DATA + 1:norma.OUT], [0]*(0xFFC))

    def test_05_traduce03(self):
        norma.loader("test/branchmacro.a")
        # falta un programa que haga algo y probar que la memoria lo contenga bien

    def test_06_traducenot(self):
        norma.loader("test/not.a")
        self.assertListEqual(norma.mem[norma.DATA : norma.DATA+1], [0])
        self.assertListEqual(norma.mem[0:3], [norma.DATA, norma.DATA, norma.OUT])
        self.assertListEqual(norma.mem[3:6], [1003, 1003, norma.IP])
        self.assertListEqual(norma.mem[6:norma.DATA], [0]*(norma.DATA-6))
        self.assertListEqual(norma.mem[norma.DATA + 1:norma.OUT], [0]*(0xFFC))


class TestCpu(unittest.TestCase):
    def setUp(self):
        reload(norma)

    def test_01_not(self):
        norma.cpu("test/not.a")
        self.assertEqual(norma.mem[norma.OUT], 0xFFFF)

    def test_02_mov(self):
        norma.cpu("test/mov.a")
        self.assertEqual(norma.mem[norma.OUT], 200)

    def test_03_xor(self):
        norma.cpu("test/xor.a")
        self.assertEqual(norma.mem[1001], 0)
        self.assertEqual(norma.mem[1002], 1)
        self.assertEqual(norma.mem[1003], 1)
        self.assertEqual(norma.mem[1004], 0)

    def test_04_lshift(self):
        norma.cpu("test/lshift.a")
        self.assertEqual(norma.mem[1001], 2)
        self.assertEqual(norma.mem[1002], 4)
        self.assertEqual(norma.mem[1003], 6)
        self.assertEqual(norma.mem[1004], 8)
        self.assertEqual(norma.mem[1005], 10)
        self.assertEqual(norma.mem[1006], 200)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConvierte)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestTraduce)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestMacros)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestCpu)
    unittest.TextTestRunner(verbosity=2).run(suite)

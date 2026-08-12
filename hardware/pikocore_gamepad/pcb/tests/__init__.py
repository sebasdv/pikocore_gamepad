# Este archivo NO es decorativo: es la condicion para que la suite corra.
#
# run_tests.py llama discover(start_dir=tests/, top_level_dir=pcb/). Con esa
# combinacion, unittest exige que tests/ sea importable como paquete. Si este
# archivo no existe, unittest tira "ImportError: Start directory is not
# importable" y NO corre ni un test.
#
# El modo de fallo es peligroso porque a primera vista se parece a un exito:
# el runner termina sin ejecutar nada. No borrar por "limpieza".

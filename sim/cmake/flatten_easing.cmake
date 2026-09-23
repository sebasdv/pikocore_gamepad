# doth/easing.h (generado por doth/generate_easing.py) tiene cadenas "else if"
# de cientos de eslabones, y MSVC corta en 128 niveles de anidamiento (error
# C1061). Como cada rama termina en return, "} else if (" -> "}\n  if (" es
# semánticamente idéntico. Se genera una copia aplanada en el build; el
# original no se toca.
function(piko_flatten_easing src dst)
  file(READ "${src}" content)
  string(REPLACE "} else if (" "}\n  if (" content "${content}")
  string(FIND "${content}" "else" leftover)
  if(NOT leftover EQUAL -1)
    message(FATAL_ERROR "${src} tiene un 'else' que no es 'else if': aplanarlo ya no es seguro")
  endif()
  file(WRITE "${dst}.tmp" "${content}")
  configure_file("${dst}.tmp" "${dst}" COPYONLY)
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${src}")
endfunction()

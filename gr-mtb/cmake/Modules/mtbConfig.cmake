INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_MTB mtb)

FIND_PATH(
    MTB_INCLUDE_DIRS
    NAMES mtb/api.h
    HINTS $ENV{MTB_DIR}/include
        ${PC_MTB_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    MTB_LIBRARIES
    NAMES gnuradio-mtb
    HINTS $ENV{MTB_DIR}/lib
        ${PC_MTB_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(MTB DEFAULT_MSG MTB_LIBRARIES MTB_INCLUDE_DIRS)
MARK_AS_ADVANCED(MTB_LIBRARIES MTB_INCLUDE_DIRS)


#pragma once

// standard C/C++ header boilerplate
#if defined(_WIN32)&&!defined(USE_STATIC_LIB_WIN)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

#ifdef __cplusplus
extern "C"{
#endif

// return 1 if auth succeed, 0 if failed
EXPORT int fuauth_setup(void* authdata,int authdata_sz);
EXPORT int fuauth_setup_with_version(void* authdata,int authdata_sz, char* version);
EXPORT int fuauth_setup_offline(void* authdata,int authdata_sz, void** offline_bundle_ptr, int* offline_bundle_sz, char* version);

EXPORT int fuauth_get_module_code(int i);

// check the auth status each frame
//   even if fuauth_setup failed, we allows this routine be called several frames
// return 1 if auth succeed, 0 if failed
EXPORT int fuauth_runtime_check();

// for internal check
EXPORT char* fuauth_get_internal_version_code();

#ifdef __cplusplus
}
#endif
@echo off
rem
rem CMake wrapper for current project, to ease the process of generating
rem project files or Makefiles
rem
rem Usage: run_cmake.bat <build_dir> <debug_runtime_output_dir> <runtime_output_dir> <source_dir> <cmake_generator>
rem
setlocal

set PWD=%cd%.

echo %PWD%
setlocal enabledelayedexpansion
for /L %%n in (1,1,20) do (
    set  shaderPath=%PWD%\shader%%n.vert
    echo !shaderPath!
    C:\VulkanSDK\1.3.216.0\Bin\glslc.exe !shaderPath! -o vert%%n.spv
)

for /L %%n in (1,1,20) do (
    set  shaderPath=%PWD%\shader%%n.frag
    echo !shaderPath!
    C:\VulkanSDK\1.3.216.0\Bin\glslc.exe !shaderPath! -o frag%%n.spv
)

endlocal

pause
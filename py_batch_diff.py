from os import listdir
import subprocess

path = "/media/FASTBIG/RenderPipeline-version_1_release/Code"
other_path = "/media/FASTBIG/python27/RenderPipeline-version_1_release/Code"
diff_dir_path = "/media/FASTBIG/RenderPipeline-version_1_release/Code/tmp"

dirs = listdir(path)

for file in dirs:
    if file.endswith(".py") and "__init__.py" not in file:
        cmd = ["diff", "-u", "{0}/{1}".format(other_path, file), "{0}/{1}".format(path, file)]
        output = subprocess.run(cmd, capture_output=True, text=True)
        if output:
            with open("{0}/{1}.diff".format(diff_dir_path, file), "w") as diff:
                diff.write(output.stdout)

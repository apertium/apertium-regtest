def merge_makefiles(file1, file2, output_file):
    try:
        # Open the output file in write mode ('w')
        with open(output_file, 'w') as outfile:
            # Open the first file and read its content
            with open(file1, 'r') as f1:
                content1 = f1.read()
                outfile.write(content1)
                outfile.write("\n")  # Optionally add a newline between files

            # Open the second file and read its content
            with open(file2, 'r') as f2:
                content2 = f2.read()
                outfile.write(content2)
                outfile.write("\n")  # Optionally add a newline after the second file

        print(f"Files have been successfully merged into {output_file}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


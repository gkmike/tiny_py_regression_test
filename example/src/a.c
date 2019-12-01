#include <assert.h>
#include <stdio.h>
int main(int argc, char *argv[])
{
   assert(argc > 1);
   char *s = argv[1];
	printf("hello world %s\n", s);
	return 0;
}

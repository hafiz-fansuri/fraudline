# GNU OpenMP runtime

`libgomp.so.1` is an unmodified GNU OpenMP runtime binary from the official Amazon Linux 2 package `libgomp-7.3.1-18.amzn2.x86_64`, obtained using the official `amazonlinux:2` container image. It is bundled because Vercel's Python runtime does not include the library required by LightGBM.

Upstream: https://gcc.gnu.org/projects/gomp/

License: GNU General Public License version 3, with GCC Runtime Library Exception version 3.1. See COPYING3 and COPYING.RUNTIME. These terms apply to the third-party runtime; they do not change the license of unrelated application code.

Corresponding source package: `gcc-7.3.1-18.amzn2.src.rpm`, available through the Amazon Linux 2 source repositories. Amazon Linux source-package retrieval: https://docs.aws.amazon.com/linux/al2/ug/compiling-software.html . Upstream GCC source: https://gcc.gnu.org/git/ .

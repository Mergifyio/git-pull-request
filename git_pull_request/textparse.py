# # -*- encoding: utf-8 -*-
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #    http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# # implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.
# import itertools
# import operator

# IGNORE_MARKER = "> ------------------------ >8 ------------------------"
# IGNORE_MARKER_DESC = (
#     "> Do not modify or remove the line above.\n"
#     "> Everything below it will be ignored.\n"
# )


# def concat_with_ignore_marker(str1, str2):
#     return (
#         str1
#         +
#         # Be sure there's a \n between str1 and the marker
#         ("\n" if str1 and str1[-1] != "\n" else "")
#         + IGNORE_MARKER
#         + "\n"
#         + IGNORE_MARKER_DESC
#         + str2
#     )


# def remove_ignore_content(s):
#     try:
#         return s[: s.index(IGNORE_MARKER)]
#     except ValueError:
#         return s

# def parse_pr_message(message):
#     message = remove_ignore_content(message)
#     message_by_line = message.split("\n")
#     if len(message) == 0:
#         return None, None
#     title = message_by_line[0]
#     body = "\n".join(itertools.dropwhile(operator.not_, message_by_line[1:]))
#     return title, body


pass

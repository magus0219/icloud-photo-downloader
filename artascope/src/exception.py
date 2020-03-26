#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22


class ArtascopeException(Exception):
    def __str__(self):
        return "[{classname}]{info}".format(
            classname=type(self).__name__,  # 通过这种方法拿到子类名
            info=".".join(
                "{k}:{v}".format(k=key, v=value) for key, value in self.__dict__.items()
            ),
        )


#   SlackSender  #
class SlackSenderException(ArtascopeException):
    def __init__(self, msg=None):
        self.msg = msg

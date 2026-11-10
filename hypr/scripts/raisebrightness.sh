#!/bin/sh
TEST=$(brightnessctl g)

brightnessctl s $(($TEST + 20000))

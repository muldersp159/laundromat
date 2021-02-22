import os
from databaseinterface import DatabaseHelper
database = DatabaseHelper('laundromat.sqlite')

f = open(r"D:\GitHub\laundromat\brickpiflask1\reads\Contacts.csv", "r").read()
lines = f.split('\n')
for line in lines:
    database.ModifyQueryHelper("INSERT INTO users (fullname, permission) VALUES (?,?);",(line,"customer"))
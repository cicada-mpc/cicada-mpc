Feature: Fields

    Scenario Outline: Field Array Creation
        When a field array is initialized with <value> and modulus <modulus> its contents should match <out> and modulus <outmod>

        Examples:
        | value                               | modulus  | out           | outmod         |
        | 1                                   | 251      | 1             | 251            |
        | [1]                                 | 251      | [1]           | 251            |
        | [1,2]                               | 251      | [1,2]         | 251            |
        | [[1,2],[3,4]]                       | 251      | [[1,2],[3,4]] | 251            |
        | [1.3]                               | 251      | [1]           | 251            |
        | [1.3, 2.8]                          | 251      | [1, 2]        | 251            |
        | FieldArray([1, 2, 3], modulus=251)  | None     | [1, 2, 3]     | 251            |


    Scenario Outline: Field Array Serialization
        When a field array is initialized with <value> and modulus <modulus> and serialized the duplicate should match

        Examples:
        | value                               | modulus  |
        | 1                                   | 251      |
        | [1]                                 | 251      |
        | [1,2]                               | 251      |
        | [[1,2],[3,4]]                       | 251      |
        | [1.3]                               | 251      |
        | [1.3, 2.8]                          | 251      |
        | FieldArray([1, 2, 3], modulus=251)  | None     |


    Scenario Outline: Addition
        Given a <field>
        When <a> is added to <b> in the field the result should match <c>

        Examples:
        | field                   | a         | b         | c        |
        | Field with modulus 251  | 1         | 1         | 2        |
        | Field with modulus 251  | 1         | 3         | 4        |
        | Field with modulus 251  | 3         | 1         | 4        |
        | Field with modulus 251  | -1        | 2         | 1        |
        | Field with modulus 251  | 2         | -1        | 1        |


    Scenario Outline: Multiplication
        Given a <field>
        When <a> is multiplied with <b> in the field the result should match <c>

        Examples:
        | field                   | a         | b         | c        |
        | Field with modulus 251  | 0         | 1         | 0        |
        | Field with modulus 251  | 1         | 1         | 1        |
        | Field with modulus 251  | 1         | 3         | 3        |
        | Field with modulus 251  | 3         | 1         | 3        |
        | Field with modulus 251  | -1        | 2         | 249      |
        | Field with modulus 251  | 2         | -1        | 249      |
        | Field with modulus 251  | -2        | -2        | 4        |


    Scenario Outline: Negation
        Given a <field>
        When <a> is negated in the field the result should match <b>

        Examples:
        | field                   | a         | b         |
        | Field with modulus 251  | 0         | 0         |
        | Field with modulus 251  | 3         | 248       |
        | Field with modulus 251  | -3        | 3         |


    Scenario Outline: Subtraction
        Given a <field>
        When <b> is subtracted from <a> in the field the result should match <c>

        Examples:
        | field                   | a         | b         | c        |
        | Field with modulus 251  | 1         | 1         | 0        |
        | Field with modulus 251  | 1         | 3         | 249      |
        | Field with modulus 251  | 3         | 1         | 2        |
        | Field with modulus 251  | -1        | 2         | 248      |
        | Field with modulus 251  | 2         | -1        | 3        |


    Scenario Outline: Zeros
        Given a <field>
        When generating FieldArray zeros with shape <shape> the result should match <result>

        Examples:
        | field                   | shape              | result                |
        | Field with modulus 251  | ()                 | 0                     |
        | Field with modulus 251  | 1                  | [0]                   |
        | Field with modulus 251  | (2, 3)             | [[0, 0, 0],[0, 0, 0]] |


    Scenario Outline: Zeros Like
        Given a <field>
        When generating FieldArray zeros like <other> the result should match <result>

        Examples:
        | field                   | other              | result                |
        | Field with modulus 251  | 3                  | 0                     |
        | Field with modulus 251  | [3, 4]             | [0, 0]                |
        | Field with modulus 251  | [[3,4,5],[5,6,7]]  | [[0, 0, 0],[0, 0, 0]] |

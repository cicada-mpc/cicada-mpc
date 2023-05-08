Feature: Arithmetic

    Scenario Outline: Field Array
        Given a <field>
	When generating a field array <x>
	Then the field array should match <x>

        Examples:
        | field                     | x                  |
        | Field with default order  | 1                  |
        | Field with default order  | [1]                |
        | Field with default order  | [1,2,3]            |
        | Field with default order  | [[1,2,3],[4,5,6]]  |


    Scenario Outline: Field Equality
        Given a <lhs>
        And a <rhs>
        Then the fields should compare <result>

        Examples:
        | lhs                       | rhs                                              | result   |
        | Field with default order  | Field with default order                         | equal    |
        | Field with default order  | Field with order 251                             | unequal  |


    Scenario Outline: Field Zeros
        Given a <field>
	When generating a field array of zeros with shape <shape>
	Then the field array should match <result>

        Examples:
        | field                           | shape              | result                |
        | Field with default order        | ()                 | 0                     |
        | Field with default order        | 1                  | [0]                   |
        | Field with default order        | (2, 3)             | [[0, 0, 0],[0, 0, 0]] |


    Scenario Outline: Field Zeros Like
        Given a <field>
        When generating a field array of zeros like <other>
	Then the field array should match <result>

        Examples:
        | field                           | other              | result                |
        | field with default order        | 3                  | 0                     |
        | field with default order        | [3, 4]             | [0, 0]                |
        | field with default order        | [[3,4,5],[5,6,7]]  | [[0, 0, 0],[0, 0, 0]] |


	#    Scenario: Encoding and Decoding None
	#        Given a FixedFieldEncoder
	#        When None is encoded and decoded the result should be None
	#
	#
	#    Scenario Outline: Subtraction
	#        Given a <encoder>
	#        When <b> is subtracted from <a> the result should match <c>
	#
	#        Examples:
	#        | encoder            | a         | b         | c        |
	#        | FixedFieldEncoder  | 1         | 1         | 0        |
	#        | FixedFieldEncoder  | 1         | 3         | -2       |
	#        | FixedFieldEncoder  | 1.2       | 3.5       | -2.3     |
	#        | FixedFieldEncoder  | 1.2       | 0         | 1.2      |
	#        | FixedFieldEncoder  | 0         | 1.2       | -1.2     |
	#
	#
	#    Scenario Outline: Negation
	#        Given a <encoder>
	#        When <a> is negated the result should match <b>
	#
	#        Examples:
	#        | encoder            | a         | b         |
	#        | FixedFieldEncoder  | 0         | 0         |
	#        | FixedFieldEncoder  | 3         | -3        |
	#        | FixedFieldEncoder  | 3.5       | -3.5      |
	#        | FixedFieldEncoder  | -3        | 3         |
	#        | FixedFieldEncoder  | -3.2      | 3.2       |
	#
	#
	#    Scenario Outline: Summation
	#        Given a <encoder>
	#        When <a> is summed the result should match <b>
	#
	#        Examples:
	#        | encoder            | a         | b         |
	#        | FixedFieldEncoder  | [1, 2, 3] | 6         |
	#
	#
	#    Scenario Outline: Untruncated Matrix Vector Multiplication
	#        Given a <encoder>
	#        When matrix <A> and vector <x> are encoded and multiplied without truncation, the decoded result should match <y>
	#
	#        Examples:
	#        | encoder           | A                           | x                           | y                 |
	#        | FixedFieldEncoder | [[1,2,3],[4,5,6],[0,0,0]]   | [1,1,1]                     | [393216,983040,0] |
	#        | FixedFieldEncoder | [0, 1, 2, 3, 4, 5, 6, 7, 8] | [0, 1, 2, 3, 4, 5, 6, 7, 8] | 13369344          |
	#
	#

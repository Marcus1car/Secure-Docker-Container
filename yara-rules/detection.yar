rule test_rule {
    strings:
        $magic = { 4D 5A }  // MZ header for PE files
    condition:
        $magic at 0
}
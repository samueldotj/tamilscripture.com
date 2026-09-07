//! Prints the SQL twin of `tamil_norm::normalize` for use in a migration.
fn main() {
    print!("{}", tamil_norm::sql_function());
}

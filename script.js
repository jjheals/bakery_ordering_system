
function onSubmit() {
  form = document.forms[0];
  loe = form.elements;
  for (var i = 0; i < loe.length; i++) {
    console.log(loe[i].name + " : " + loe[i].value);
  }
}
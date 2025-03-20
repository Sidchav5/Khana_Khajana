def submit():
    if request.method == 'POST':
        type = request.form['type']
        name = request.form['name']
        description = request.form['description']
        ingredients = request.form['ingredients']
        time = request.form['time']
        instructions = request.form['instructions']
        photo = request.files['photo']

        # Convert the image to base64
        if photo and allowed_file(photo.filename):
            photo_base64 = base64.b64encode(photo.read()).decode('utf-8')
        else:
            flash('Invalid image file!', 'danger')
            return redirect(url_for('post_it'))

        # Save to database with user_id
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO recipes (type, name, description, ingredients, time, instructions, photo, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (type, name, description, ingredients, time, instructions, photo_base64, current_user.id)
        )
        mysql.connection.commit()
        cur.close()

        flash('Recipe submitted successfully!', 'success')
        return redirect(url_for('post_it'))